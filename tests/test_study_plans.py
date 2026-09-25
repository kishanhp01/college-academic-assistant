from datetime import date, timedelta
from app.study_plans.models import StudyPlanRequest, Subject
from app.study_plans.planner import generate_study_plan
from app.study_plans.workflow import build_study_plan_graph


def test_study_plan_generation_is_structured():
    today = date(2026, 1, 1)
    request = StudyPlanRequest(subjects=[Subject(name="Math", difficulty=5), Subject(name="History", difficulty=2)],
                               exam_date=today + timedelta(days=3), available_hours_per_day=4,
                               preferences="Morning sessions")
    plan = generate_study_plan(request, today=today)
    assert plan.exam_date == request.exam_date
    assert len(plan.sessions) == 6
    assert sum(s.hours for s in plan.sessions if s.date == today) == 4


def test_study_plan_graph_runs():
    today = date(2026, 1, 1)
    request = StudyPlanRequest(subjects=[Subject(name="Physics", difficulty=4)],
                               exam_date=today + timedelta(days=2), available_hours_per_day=2)
    result = build_study_plan_graph(lambda req: generate_study_plan(req, today=today)).invoke({"request": request})
    assert len(result["plan"].sessions) == 2
