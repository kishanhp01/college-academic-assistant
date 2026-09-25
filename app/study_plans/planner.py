from datetime import date, timedelta

from app.study_plans.models import StudyPlan, StudyPlanRequest, StudySession


def generate_study_plan(request: StudyPlanRequest, today: date | None = None) -> StudyPlan:
    """Create an even, difficulty/priority-weighted plan through the day before the exam."""
    start = today or date.today()
    days = (request.exam_date - start).days
    if days <= 0:
        raise ValueError("The exam date must be after today.")
    if not request.subjects:
        raise ValueError("Add at least one subject.")
    weights = [subject.difficulty * subject.priority for subject in request.subjects]
    total = sum(weights)
    sessions = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for subject, weight in zip(request.subjects, weights):
            hours = round(request.available_hours_per_day * weight / total, 2)
            sessions.append(StudySession(date=day, subject=subject.name, hours=hours,
                                         activity="Review key concepts and solve practice questions"))
    return StudyPlan(exam_date=request.exam_date, assumptions=[
        f"Plan starts {start.isoformat()} and ends the day before the exam.",
        "Daily study time is divided in proportion to subject difficulty and priority.",
        f"Preferences: {request.preferences or 'No preferences specified.'}",
    ], sessions=sessions)


def modify_study_plan(plan: StudyPlan, *, missed_sessions: list[str] | None = None,
                      available_hours_per_day: float | None = None, exam_date=None,
                      changed_priorities: dict[str, int] | None = None, today: date | None = None) -> StudyPlan:
    """Regenerate a plan using updated constraints and adjust for missed work."""
    start = today or date.today()
    new_exam_date = exam_date or plan.exam_date
    subjects_by_name = {}
    for session in plan.sessions:
        subjects_by_name.setdefault(session.subject, 1)
    if not subjects_by_name:
        raise ValueError("Cannot modify an empty study plan.")
    priorities = dict(changed_priorities or {})
    missed = set(missed_sessions or [])
    for name in subjects_by_name:
        if name in missed and name not in priorities:
            priorities[name] = 5
    from app.study_plans.models import Subject
    subjects = [Subject(name=name, difficulty=3, priority=priorities.get(name, 3)) for name in subjects_by_name]
    usual_hours = max((sum(s.hours for s in plan.sessions if s.date == day)
                       for day in {s.date for s in plan.sessions}), default=1.0)
    request = StudyPlanRequest(subjects=subjects, exam_date=new_exam_date,
                               available_hours_per_day=available_hours_per_day or usual_hours,
                               preferences="Modified plan; missed subjects receive highest priority: " + ", ".join(missed))
    updated = generate_study_plan(request, today=start)
    if missed:
        updated.assumptions.append("Missed subjects receive additional study time where remaining days allow: " + ", ".join(sorted(missed)))
    if changed_priorities:
        updated.assumptions.append("Updated priorities applied: " + str(changed_priorities))
    return updated
