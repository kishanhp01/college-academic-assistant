from unittest.mock import Mock

from langchain_core.documents import Document
import pytest

from app.assistant import answering, router
from app.workflows import academic
from app.workflows.academic import build_academic_graph


class FakeRetriever:
    def __init__(self):
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        return [
            Document(
                page_content="Attendance must be at least 85%.",
                metadata={"source": "regulations.pdf", "page": 0},
            )
        ]


def test_college_question_uses_rag_and_preserves_existing_result_fields():
    retriever = FakeRetriever()
    answer = Mock(return_value="FAKE COLLEGE ANSWER")

    result = build_academic_graph(retriever, answer).invoke(
        {"question": "  What is the attendance requirement?  "}
    )

    assert result["question"] == "What is the attendance requirement?"
    assert result["analyzed_query"] == result["question"]
    assert result["route"] == "college"
    assert result["answer"] == "FAKE COLLEGE ANSWER"
    assert result["sources"] == [
        {
            "label": "regulations.pdf (page 1)",
            "excerpt": "Attendance must be at least 85%.",
        }
    ]
    assert retriever.queries == [result["question"]]
    answer.assert_called_once()
    assert answer.call_args.args[0] == result["question"]
    assert answer.call_args.args[1][0].page_content == "Attendance must be at least 85%."


def test_college_branch_invokes_router_and_not_general_answerer():
    retriever = FakeRetriever()
    answer = Mock(return_value="FAKE COLLEGE ANSWER")
    general_answer = Mock(side_effect=AssertionError("general answerer should not run"))
    route = Mock(wraps=router.route_question)

    result = build_academic_graph(
        retriever,
        answer,
        general_answer_fn=general_answer,
        router_fn=route,
    ).invoke({"question": "What is the attendance requirement?"})

    assert result["route"] == "college"
    route.assert_called_once_with("What is the attendance requirement?")
    assert retriever.queries == ["What is the attendance requirement?"]
    answer.assert_called_once()
    general_answer.assert_not_called()


def test_general_question_uses_general_answerer_without_constructing_retriever(monkeypatch):
    general_answerer = Mock(
        return_value={"answer": "FAKE GENERAL ANSWER", "source": "general_llm"}
    )
    retriever_constructor = Mock(side_effect=AssertionError("retriever should not be created"))
    route = Mock(wraps=router.route_question)
    monkeypatch.setattr(academic, "answer_general_question", general_answerer)
    monkeypatch.setattr(academic, "AcademicRetriever", retriever_constructor)

    result = build_academic_graph(router_fn=route).invoke(
        {"question": "What is polymorphism in Java?"}
    )

    assert result["question"] == "What is polymorphism in Java?"
    assert result["route"] == "general"
    assert result["answer"] == "FAKE GENERAL ANSWER"
    assert result["source"] == "general_llm"
    assert result["sources"] == []
    general_answerer.assert_called_once_with("What is polymorphism in Java?")
    retriever_constructor.assert_not_called()
    route.assert_called_once_with("What is polymorphism in Java?")


def test_general_answerer_can_be_injected_without_changing_graph_interface():
    general_answerer = Mock(
        return_value={"answer": "FAKE GENERAL ANSWER", "source": "general_llm"}
    )

    result = build_academic_graph(general_answer_fn=general_answerer).invoke(
        {"question": "Explain binary search."}
    )

    assert result["route"] == "general"
    assert result["answer"] == "FAKE GENERAL ANSWER"
    assert result["source"] == "general_llm"
    general_answerer.assert_called_once_with("Explain binary search.")


def test_mse_question_uses_college_branch():
    retriever = FakeRetriever()
    answer = Mock(return_value="FAKE COLLEGE ANSWER")
    general_answer = Mock(side_effect=AssertionError("general answerer should not run"))
    route = Mock(wraps=router.route_question)

    result = build_academic_graph(
        retriever,
        answer,
        general_answer_fn=general_answer,
        router_fn=route,
    ).invoke({"question": "When is MSE 2?"})

    assert result["route"] == "college"
    route.assert_called_once_with("When is MSE 2?")
    assert retriever.queries == ["When is MSE 2?"]
    answer.assert_called_once()
    general_answer.assert_not_called()


def test_no_retrieved_documents_preserve_safe_college_fallback():
    retriever = Mock()
    retriever.retrieve.return_value = []
    answer = Mock(wraps=answering.generate_answer)
    general_answer = Mock(side_effect=AssertionError("general answerer should not run"))

    result = build_academic_graph(
        retriever,
        answer,
        general_answer_fn=general_answer,
    ).invoke({"question": "What is the attendance requirement?"})

    assert result["route"] == "college"
    assert result["answer"] == answering.INSUFFICIENT_CONTEXT
    assert result["sources"] == []
    retriever.retrieve.assert_called_once_with("What is the attendance requirement?")
    answer.assert_called_once_with("What is the attendance requirement?", [])
    general_answer.assert_not_called()


def test_empty_question_preserves_router_value_error():
    with pytest.raises(ValueError, match="Question cannot be empty"):
        build_academic_graph().invoke({"question": ""})


def test_default_streamlit_graph_interface_returns_expected_fields(monkeypatch):
    general_answerer = Mock(
        return_value={"answer": "FAKE GENERAL ANSWER", "source": "general_llm"}
    )
    retriever_constructor = Mock(side_effect=AssertionError("retriever should not be created"))
    monkeypatch.setattr(academic, "answer_general_question", general_answerer)
    monkeypatch.setattr(academic, "AcademicRetriever", retriever_constructor)

    result = build_academic_graph().invoke({"question": "What is polymorphism?"})

    assert {
        "answer",
        "sources",
        "analyzed_query",
        "question",
        "route",
        "source",
    }.issubset(result)
    assert result["answer"] == "FAKE GENERAL ANSWER"
    assert result["sources"] == []
    assert result["analyzed_query"] == "What is polymorphism?"
    assert result["question"] == "What is polymorphism?"
    assert result["route"] == "general"
    assert result["source"] == "general_llm"
    general_answerer.assert_called_once_with("What is polymorphism?")
    retriever_constructor.assert_not_called()
