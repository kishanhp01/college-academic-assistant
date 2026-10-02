import re


_COLLEGE_PATTERNS = (
    re.compile(r"\b(?:college|nmamit|nitte|campus|university)\b", re.IGNORECASE),
    re.compile(
        r"\battendance\b|\b(?:miss|skip)\s+(?:my\s+)?classes\b"
        r"|\bclasses\b.{0,20}\b(?:miss|skip)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:mse|cie)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:academic regulations?|academic leave|college rules?|course registration|"
        r"internal marks|academic calendar|admissions?|fees?|timetable)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:department|faculty|professor|hod)\b", re.IGNORECASE),
    re.compile(r"\bsemester\b", re.IGNORECASE),
    re.compile(
        r"\b(?:exams?|examinations?)\b.{0,30}\b(?:date|schedule|rules?|requirement)\b"
        r"|\b(?:date|schedule|rules?|requirement)\b.{0,30}\b(?:exams?|examinations?)\b"
        r"|\bmy\s+(?:exam|examination)\b",
        re.IGNORECASE,
    ),
)

_GENERAL_CONTEXT_PATTERNS = (
    re.compile(r"\bexam(?:ination)?\b.{0,35}\bsoftware testing\b", re.IGNORECASE),
    re.compile(r"\bcourse\b.{0,35}\bmachine learning\b", re.IGNORECASE),
)


def route_question(question: str) -> str:
    """Classify a question as college-specific or general using simple text rules."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question cannot be empty.")

    if any(pattern.search(normalized_question) for pattern in _COLLEGE_PATTERNS):
        return "college"

    if any(pattern.search(normalized_question) for pattern in _GENERAL_CONTEXT_PATTERNS):
        return "general"

    return "general"
