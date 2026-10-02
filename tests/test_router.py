import ast
from pathlib import Path

import pytest

from app.assistant.router import route_question


@pytest.mark.parametrize(
    "question",
    [
        "What is the attendance requirement?",
        "When is MSE 2?",
        "How do I apply for academic leave?",
        "Who is the HOD of CSE?",
        "What are the college examination rules?",
        "Tell me about the CSE department at NMAMIT.",
        "How many classes can I miss?",
        "What is the timetable for this semester?",
        "What is the course registration process?",
    ],
)
def test_routes_college_specific_questions(question):
    assert route_question(question) == "college"


@pytest.mark.parametrize(
    "question",
    [
        "What is polymorphism in Java?",
        "Explain binary search.",
        "What is normalization in DBMS?",
        "Explain TCP.",
        "What is an operating system?",
        "What is an exam in software testing?",
        "What is a course in machine learning?",
        "How does a student learn data structures?",
    ],
)
def test_routes_general_academic_questions(question):
    assert route_question(question) == "general"


@pytest.mark.parametrize("question", ["", " ", "\n\t "])
def test_empty_question_raises_value_error(question):
    with pytest.raises(ValueError, match="Question cannot be empty"):
        route_question(question)


def test_router_has_no_retrieval_or_model_framework_imports():
    source_path = Path(__file__).parents[1] / "app" / "assistant" / "router.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(
        module.startswith(("app.retrieval", "faiss", "langchain_huggingface", "langgraph"))
        for module in imported_modules
    )
