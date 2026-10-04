from flask import Blueprint, current_app, g, jsonify, request, session

from app.api.authentication import require_auth
from app.api.auth_service import (
    AuthenticationDatabaseError,
    DuplicateUserError,
    RegistrationDatabaseError,
    RegistrationValidationError,
    authenticate_user,
    register_user,
)
from app.api.chat_service import (
    AcademicChatService,
    AssistantConfigurationError,
    ChatGraphError,
    ChatRequestError,
    KnowledgeIndexUnavailableError,
)
from app.api.study_plan_service import StudyPlanInputError, StudyPlanService, StudyPlanServiceError
from app.persistence.chat_history import (
    ChatHistoryError,
    ChatHistoryLimitError,
    get_user_chat_history,
    parse_history_limit,
)


api_blueprint = Blueprint("api", __name__, url_prefix="/api")


@api_blueprint.get("/health")
def health_check():
    return jsonify(status="ok")


@api_blueprint.post("/auth/register")
def register():
    try:
        user = register_user(
            request.get_json(silent=True),
            current_app.extensions["database_session_factory"],
        )
    except RegistrationValidationError as error:
        return jsonify(error=str(error)), 400
    except DuplicateUserError as error:
        return jsonify(error=str(error)), 409
    except RegistrationDatabaseError:
        current_app.logger.error("Database error during user registration")
        return jsonify(error="Registration could not be completed."), 500

    return jsonify(message="Registration successful", user=user), 201


@api_blueprint.post("/auth/login")
def login():
    try:
        user = authenticate_user(
            request.get_json(silent=True),
            current_app.extensions["database_session_factory"],
        )
    except AuthenticationDatabaseError:
        current_app.logger.error("Database error during user login")
        return jsonify(error="Authentication is temporarily unavailable."), 500

    if user is None:
        return jsonify(error="Invalid email or password"), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify(message="Login successful", user=user), 200


@api_blueprint.post("/auth/logout")
def logout():
    session.clear()
    return jsonify(message="Logout successful"), 200


@api_blueprint.get("/auth/me")
@require_auth
def authenticated_user():
    return jsonify(user=g.current_user), 200


@api_blueprint.post("/chat")
@require_auth
def chat():
    chat_service: AcademicChatService = current_app.extensions["academic_chat_service"]
    try:
        result, history_saved = chat_service.answer_for_user(
            request.get_json(silent=True),
            g.current_user["id"],
            current_app.extensions["database_session_factory"],
        )
    except ChatRequestError as error:
        return jsonify(error=str(error)), 400
    except KnowledgeIndexUnavailableError:
        current_app.logger.warning("Academic chat requested without a built college index")
        return jsonify(error="The college knowledge index is unavailable."), 503
    except AssistantConfigurationError:
        current_app.logger.error("The academic assistant provider is not configured")
        return jsonify(error="The academic assistant is not configured correctly."), 503
    except ChatGraphError as error:
        current_app.logger.error("Academic graph failed (%s)", error.diagnostic_type)
        return jsonify(error="The academic assistant could not process the request."), 500
    except Exception as error:
        current_app.logger.error("Chat endpoint failed (%s)", type(error).__name__)
        return jsonify(error="The academic assistant could not process the request."), 500

    if not history_saved:
        current_app.logger.warning(
            "Chat response returned successfully, but its history record was not saved"
        )
    return jsonify(result), 200


@api_blueprint.get("/chat/history")
@require_auth
def chat_history():
    limits = request.args.getlist("limit")
    if len(limits) > 1:
        return jsonify(error="Provide the limit parameter only once."), 400

    try:
        limit = parse_history_limit(limits[0] if limits else None)
    except ChatHistoryLimitError as error:
        return jsonify(error=str(error)), 400

    try:
        messages = get_user_chat_history(
            g.current_user["id"],
            current_app.extensions["database_session_factory"],
            limit,
        )
    except ChatHistoryError:
        current_app.logger.error("Database error while loading chat history")
        return jsonify(error="Chat history is temporarily unavailable."), 500

    return jsonify(messages=messages), 200


@api_blueprint.post("/study-plan")
@require_auth
def generate_study_plan():
    study_plan_service: StudyPlanService = current_app.extensions["study_plan_service"]
    try:
        plan = study_plan_service.generate(request.get_json(silent=True))
    except StudyPlanInputError as error:
        return jsonify(error=str(error)), 400
    except StudyPlanServiceError:
        current_app.logger.error("Study plan generation failed")
        return jsonify(error="Study plan generation failed."), 500
    except Exception as error:
        current_app.logger.error("Study plan endpoint failed (%s)", type(error).__name__)
        return jsonify(error="Study plan generation failed."), 500

    return jsonify(plan=plan), 200


@api_blueprint.post("/study-plan/modify")
@require_auth
def modify_study_plan():
    study_plan_service: StudyPlanService = current_app.extensions["study_plan_service"]
    try:
        plan = study_plan_service.modify(request.get_json(silent=True))
    except StudyPlanInputError as error:
        return jsonify(error=str(error)), 400
    except StudyPlanServiceError:
        current_app.logger.error("Study plan modification failed")
        return jsonify(error="Study plan modification failed."), 500
    except Exception as error:
        current_app.logger.error("Study plan endpoint failed (%s)", type(error).__name__)
        return jsonify(error="Study plan modification failed."), 500

    return jsonify(plan=plan), 200
