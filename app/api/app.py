import secrets
from pathlib import Path

from flask import Flask, send_from_directory

from app.api.chat_service import AcademicChatService
from app.api.routes import api_blueprint
from app.api.study_plan_service import StudyPlanService
from app.configuration.settings import get_settings
from app.persistence.database import create_session_factory, initialize_database

FRONTEND_DIRECTORY = Path(__file__).resolve().parents[2] / "frontend"


def create_app(config: dict[str, object] | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIRECTORY),
        static_url_path="",
    )
    settings = get_settings()
    app.config.from_mapping(
        DATABASE_URL=settings.database_url,
        SECRET_KEY=settings.flask_secret_key or None,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=settings.session_cookie_secure,
    )
    if config:
        app.config.update(config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = secrets.token_urlsafe(32)
        app.logger.warning(
            "FLASK_SECRET_KEY is unset; using an ephemeral development key. "
            "Configure a persistent secret before production deployment."
        )

    database_engine = initialize_database(app.config["DATABASE_URL"])
    app.extensions["database_engine"] = database_engine
    app.extensions["database_session_factory"] = create_session_factory(database_engine)
    app.extensions["academic_chat_service"] = AcademicChatService()
    app.extensions["study_plan_service"] = StudyPlanService()

    @app.get("/")
    def frontend_home():
        return send_from_directory(FRONTEND_DIRECTORY, "login.html")

    app.register_blueprint(api_blueprint)
    return app
