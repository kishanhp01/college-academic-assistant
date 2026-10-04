from datetime import date, timedelta

import pytest

from app.api.study_plan_service import (
    StudyPlanInputError,
    StudyPlanService,
    StudyPlanServiceError,
)
from app.study_plans.models import StudyPlanRequest
from app.study_plans.planner import generate_study_plan, modify_study_plan
from app.study_plans.workflow import build_study_plan_graph


def _request(exam_date=None):
    return {
        "subjects": [
            {"name": "Math", "difficulty": 5, "priority": 4},
            {"name": "History", "difficulty": 2, "priority": 3},
        ],
        "exam_date": (exam_date or date.today() + timedelta(days=3)).isoformat(),
        "available_hours_per_day": 4,
        "preferences": "Morning sessions",
    }


def _deterministic_graph():
    fixed_today = date(2026, 1, 1)
    return build_study_plan_graph(
        generator=lambda request: generate_study_plan(request, today=fixed_today)
    )


def test_generation_uses_existing_workflow_and_returns_json_safe_plan():
    service = StudyPlanService(
        graph_factory=_deterministic_graph,
        today_provider=lambda: date(2026, 1, 1),
    )

    result = service.generate(_request(date(2026, 1, 4)))

    assert result["exam_date"] == "2026-01-04"
    assert result["sessions"][0]["date"] == "2026-01-01"
    assert result["sessions"][0]["subject"] == "Math"
    assert len(result["sessions"]) == 6
    assert result["assumptions"]
    assert isinstance(result, dict)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"subjects": [], "exam_date": "2027-01-01", "available_hours_per_day": 3},
        {
            "subjects": [{"name": "Math", "difficulty": 8}],
            "exam_date": "2027-01-01",
            "available_hours_per_day": 3,
        },
        {
            "subjects": [{"name": "Math", "difficulty": 3}],
            "exam_date": "not-a-date",
            "available_hours_per_day": 3,
        },
        {
            "subjects": [{"name": "Math", "difficulty": 3}],
            "exam_date": "2020-01-01",
            "available_hours_per_day": 3,
        },
        {
            "subjects": [{"name": "Math", "difficulty": 3}],
            "exam_date": "2027-01-01",
            "available_hours_per_day": 0,
        },
    ],
)
def test_invalid_generation_input_is_rejected(payload):
    with pytest.raises(StudyPlanInputError):
        StudyPlanService().generate(payload)


def test_empty_subject_names_are_rejected():
    payload = _request()
    payload["subjects"][0]["name"] = "  "

    with pytest.raises(StudyPlanInputError, match="Subject names"):
        StudyPlanService().generate(payload)


def test_planner_graph_failures_become_safe_service_errors():
    def fail_graph_factory():
        raise RuntimeError("internal implementation details")

    with pytest.raises(StudyPlanServiceError) as raised:
        StudyPlanService(graph_factory=fail_graph_factory).generate(_request())

    assert "internal implementation details" not in str(raised.value)


def test_value_error_from_planner_is_not_exposed_as_client_validation():
    class InvalidGraph:
        def invoke(self, state):
            raise ValueError("private planner internals")

    with pytest.raises(StudyPlanServiceError) as raised:
        StudyPlanService(graph_factory=InvalidGraph).generate(_request())

    assert "private planner internals" not in str(raised.value)


def test_existing_plan_modifier_handles_plan_changes():
    today = date.today()
    original = generate_study_plan(
        StudyPlanRequest.model_validate(_request(today + timedelta(days=5)))
    )
    service = StudyPlanService(modifier=modify_study_plan)

    revised = service.modify(
        {
            "plan": original.model_dump(mode="json"),
            "missed_sessions": ["Math"],
            "available_hours_per_day": 5,
            "exam_date": (today + timedelta(days=6)).isoformat(),
            "changed_priorities": {"History": 4},
        }
    )

    assert revised["exam_date"] == (today + timedelta(days=6)).isoformat()
    assert revised["sessions"]
    assert any("Missed subjects" in item for item in revised["assumptions"])
    assert any("Updated priorities" in item for item in revised["assumptions"])


def test_invalid_modification_input_is_rejected():
    with pytest.raises(StudyPlanInputError):
        StudyPlanService().modify({"missed_sessions": ["Math"]})

    plan = generate_study_plan(
        StudyPlanRequest.model_validate(_request(date.today() + timedelta(days=3)))
    )
    with pytest.raises(StudyPlanInputError, match="priorities"):
        StudyPlanService().modify(
            {"plan": plan.model_dump(mode="json"), "changed_priorities": {"Math": 9}}
        )


def test_modifier_failure_becomes_safe_service_error():
    def fail_modifier(*args, **kwargs):
        raise RuntimeError("private planner failure")

    plan = generate_study_plan(
        StudyPlanRequest.model_validate(_request(date.today() + timedelta(days=3)))
    )
    service = StudyPlanService(modifier=fail_modifier)

    with pytest.raises(StudyPlanServiceError) as raised:
        service.modify({"plan": plan.model_dump(mode="json")})

    assert "private planner failure" not in str(raised.value)
