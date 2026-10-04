import json
from unittest.mock import Mock

import pytest
from langchain_core.documents import Document

from app.api.chat_service import (
    MAX_QUESTION_LENGTH,
    AcademicChatService,
    AssistantConfigurationError,
    ChatGraphError,
    ChatRequestError,
    KnowledgeIndexUnavailableError,
    serialize_graph_result,
    validate_question_payload,
)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"question": None},
        {"question": 12},
        {"question": ""},
        {"question": " \t\n "},
        {"question": "q" * (MAX_QUESTION_LENGTH + 1)},
    ],
)
def test_question_validation_rejects_invalid_payloads(payload):
    with pytest.raises(ChatRequestError):
        validate_question_payload(payload)


def test_question_validation_trims_whitespace():
    assert validate_question_payload({"question": "  What is attendance?  "}) == (
        "What is attendance?"
    )


class FakeGraph:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.inputs = []

    def invoke(self, state):
        self.inputs.append(state)
        if self.error:
            raise self.error
        return self.result


def test_college_result_is_student_facing_and_json_safe():
    document = Document(
        page_content="Private internal graph document object",
        metadata={"source": "rules.pdf"},
    )
    graph = FakeGraph(
        result={
            "question": "ignored graph question",
            "analyzed_query": "attendance rules",
            "route": "college",
            "answer": "Use the college rules.",
            "source": "college_documents",
            "sources": [
                {"label": "rules.pdf (page 1)", "excerpt": "Attendance requirements."},
                document,
            ],
            "documents": [document],
            "prompt": "must not be returned",
        }
    )
    graph_factory = Mock(return_value=graph)
    service = AcademicChatService(graph_factory=graph_factory)

    result = service.answer({"question": "  What is the attendance requirement?  "})

    assert result == {
        "answer": "Use the college rules.",
        "question": "What is the attendance requirement?",
        "analyzed_query": "attendance rules",
        "route": "college",
        "source": "college_documents",
        "sources": [
            {"label": "rules.pdf (page 1)", "excerpt": "Attendance requirements."}
        ],
    }
    json.dumps(result)
    assert graph.inputs == [{"question": "What is the attendance requirement?"}]
    graph_factory.assert_called_once_with()


def test_general_result_is_returned_without_college_sources():
    graph = FakeGraph(
        result={
            "answer": "Polymorphism allows related types to share an interface.",
            "analyzed_query": "What is polymorphism?",
            "route": "general",
            "source": "general_llm",
            "sources": [],
            "documents": [Document(page_content="must be dropped")],
        }
    )
    service = AcademicChatService(graph_factory=lambda: graph)

    result = service.answer({"question": "What is polymorphism?"})

    assert result["route"] == "general"
    assert result["source"] == "general_llm"
    assert result["sources"] == []
    assert "documents" not in result


def test_graph_is_reused_by_the_app_scoped_service():
    graph = FakeGraph(
        result={"answer": "Answer", "route": "general", "sources": []}
    )
    graph_factory = Mock(return_value=graph)
    service = AcademicChatService(graph_factory=graph_factory)

    service.answer({"question": "First question"})
    service.answer({"question": "Second question"})

    graph_factory.assert_called_once_with()
    assert graph.inputs == [
        {"question": "First question"},
        {"question": "Second question"},
    ]


@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        (FileNotFoundError("private index path"), KnowledgeIndexUnavailableError),
        (ValueError("private provider details"), AssistantConfigurationError),
        (RuntimeError("private stack details"), ChatGraphError),
    ],
)
def test_graph_failures_are_converted_to_safe_service_errors(error, expected_error):
    service = AcademicChatService(graph_factory=lambda: FakeGraph(error=error))

    with pytest.raises(expected_error) as raised:
        service.answer({"question": "What is attendance?"})

    assert "private" not in str(raised.value)


def test_serialize_graph_result_discards_invalid_sources_and_internal_state():
    result = serialize_graph_result(
        {
            "answer": "Answer",
            "route": "general",
            "sources": [None, 42, {"metadata": {"private": True}}, "text source"],
            "internal_state": {"private": True},
        },
        "Question",
    )

    assert result["sources"] == ["text source"]
    assert set(result) == {
        "answer",
        "question",
        "analyzed_query",
        "route",
        "source",
        "sources",
    }
