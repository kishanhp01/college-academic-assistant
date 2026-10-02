from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.assistant import general_answering


@pytest.mark.parametrize(
    "question",
    [
        "What is polymorphism in Java?",
        "Explain binary search in simple terms.",
        "What is normalization in DBMS?",
    ],
)
def test_general_answer_uses_configured_llm_without_retrieval(monkeypatch, question):
    response_text = "A clear explanation for the student's question."
    fake_model = Mock()
    fake_model.invoke.return_value = SimpleNamespace(content=response_text)
    create_model = Mock(return_value=fake_model)
    monkeypatch.setattr(general_answering, "create_chat_model", create_model)

    result = general_answering.answer_general_question(question)

    assert isinstance(result, dict)
    assert result["answer"] == response_text
    assert result["source"] == "general_llm"
    create_model.assert_called_once_with()
    prompt = fake_model.invoke.call_args.args[0]
    assert question in prompt
    assert "college-specific" in prompt


@pytest.mark.parametrize("question", ["", "   ", "\n\t "])
def test_general_answer_rejects_empty_question_without_calling_llm(monkeypatch, question):
    create_model = Mock()
    monkeypatch.setattr(general_answering, "create_chat_model", create_model)

    with pytest.raises(ValueError, match="Question cannot be empty"):
        general_answering.answer_general_question(question)

    create_model.assert_not_called()
