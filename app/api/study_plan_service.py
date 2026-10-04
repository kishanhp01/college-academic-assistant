from datetime import date
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from app.study_plans.models import StudyPlan, StudyPlanRequest
from app.study_plans.planner import modify_study_plan
from app.study_plans.workflow import build_study_plan_graph


class StudyPlanInputError(ValueError):
    """Raised when a study-plan request does not match the planner's input models."""


class StudyPlanServiceError(RuntimeError):
    """Raised when existing study-planning code fails unexpectedly."""


class _PlanModificationRequest(BaseModel):
    """API form of the arguments already supported by modify_study_plan()."""

    plan: StudyPlan
    missed_sessions: list[str] = Field(default_factory=list)
    available_hours_per_day: float | None = Field(default=None, gt=0)
    exam_date: date | None = None
    changed_priorities: dict[str, int] | None = None


def _format_validation_errors(error: ValidationError) -> str:
    details = []
    for issue in error.errors(include_input=False, include_context=False):
        field = ".".join(str(part) for part in issue["loc"])
        details.append(f"{field}: {issue['msg']}" if field else issue["msg"])
    return "; ".join(details) or "Invalid study-plan input."


def _require_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise StudyPlanInputError("A JSON object is required.")
    return payload


def _serialize_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, StudyPlan):
        raise StudyPlanServiceError("The planner returned an invalid plan.")
    return plan.model_dump(mode="json")


class StudyPlanService:
    """Adapt Flask JSON payloads to the existing planner models and workflow."""

    def __init__(
        self,
        graph_factory: Callable[[], Any] | None = None,
        modifier: Callable[..., StudyPlan] | None = None,
        today_provider: Callable[[], date] | None = None,
    ):
        self._graph_factory = graph_factory or build_study_plan_graph
        self._modifier = modifier or modify_study_plan
        self._today_provider = today_provider or date.today
        self._graph: Any | None = None

    def generate(self, payload: Any) -> dict[str, Any]:
        data = _require_object(payload)
        try:
            request = StudyPlanRequest.model_validate(data)
        except ValidationError as error:
            raise StudyPlanInputError(_format_validation_errors(error)) from None

        if not request.subjects:
            raise StudyPlanInputError("Add at least one subject.")
        if any(not subject.name.strip() for subject in request.subjects):
            raise StudyPlanInputError("Subject names cannot be empty.")
        if request.exam_date <= self._today_provider():
            raise StudyPlanInputError("The exam date must be after today.")

        try:
            if self._graph is None:
                self._graph = self._graph_factory()
            result = self._graph.invoke({"request": request})
        except Exception:
            raise StudyPlanServiceError("Study plan generation failed.") from None

        return _serialize_plan(result.get("plan") if isinstance(result, dict) else None)

    def modify(self, payload: Any) -> dict[str, Any]:
        data = _require_object(payload)
        try:
            request = _PlanModificationRequest.model_validate(data)
        except ValidationError as error:
            raise StudyPlanInputError(_format_validation_errors(error)) from None

        if any(not subject.strip() for subject in request.missed_sessions):
            raise StudyPlanInputError("Missed subject names cannot be empty.")
        if request.changed_priorities is not None:
            for subject, priority in request.changed_priorities.items():
                if not subject.strip() or not 1 <= priority <= 5:
                    raise StudyPlanInputError(
                        "Changed priorities must use subject names and values from 1 to 5."
                    )
        if not request.plan.sessions:
            raise StudyPlanInputError("Cannot modify an empty study plan.")
        if (request.exam_date or request.plan.exam_date) <= self._today_provider():
            raise StudyPlanInputError("The exam date must be after today.")

        try:
            plan = self._modifier(
                request.plan,
                missed_sessions=request.missed_sessions or None,
                available_hours_per_day=request.available_hours_per_day,
                exam_date=request.exam_date,
                changed_priorities=request.changed_priorities,
            )
        except Exception:
            raise StudyPlanServiceError("Study plan modification failed.") from None

        return _serialize_plan(plan)
