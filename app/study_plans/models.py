from datetime import date
from pydantic import BaseModel, Field


class Subject(BaseModel):
    name: str
    difficulty: int = Field(ge=1, le=5, description="1 is easiest; 5 is hardest")
    priority: int = Field(default=3, ge=1, le=5)


class StudyPlanRequest(BaseModel):
    subjects: list[Subject]
    exam_date: date
    available_hours_per_day: float = Field(gt=0)
    preferences: str = ""


class StudySession(BaseModel):
    date: date
    subject: str
    hours: float = Field(gt=0)
    activity: str


class StudyPlan(BaseModel):
    exam_date: date
    assumptions: list[str] = []
    sessions: list[StudySession]
