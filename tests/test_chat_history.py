import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import OperationalError

from app.api.chat_service import AcademicChatService, ChatGraphError
from app.persistence.chat_history import (
    DEFAULT_HISTORY_LIMIT,
    ChatHistoryError,
    ChatHistoryLimitError,
    get_user_chat_history,
    parse_history_limit,
    save_chat_message,
)
from app.persistence.database import (
    ChatMessage,
    User,
    create_session_factory,
    initialize_database,
)


@pytest.fixture
def history_database():
    engine = initialize_database("sqlite:///:memory:")
    yield engine, create_session_factory(engine)
    engine.dispose()


def _create_user(session_factory, username):
    with session_factory() as session:
        user = User(
            username=username,
            email=f"{username}@example.test",
            password_hash="test-hash",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def _chat_result(question="Question", answer="Answer"):
    return {
        "question": question,
        "answer": answer,
        "route": "general",
        "source": "general_llm",
        "sources": [],
    }


def test_database_initialization_creates_chat_message_table(history_database):
    engine, _ = history_database

    assert "chat_messages" in inspect(engine).get_table_names()
    foreign_keys = inspect(engine).get_foreign_keys("chat_messages")
    assert foreign_keys[0]["referred_table"] == "users"


def test_chat_history_creation_stores_public_fields_and_timestamp(history_database):
    _, session_factory = history_database
    user_id = _create_user(session_factory, "student")

    message = save_chat_message(user_id, _chat_result(), session_factory)

    assert message["id"] == 1
    assert message["question"] == "Question"
    assert message["answer"] == "Answer"
    assert message["route"] == "general"
    assert message["source"] == "general_llm"
    assert message["created_at"]
    assert "user_id" not in message


def test_chat_history_cannot_reference_a_nonexistent_user(history_database):
    _, session_factory = history_database

    with pytest.raises(ChatHistoryError):
        save_chat_message(999, _chat_result(), session_factory)


def test_chat_history_is_isolated_by_user(history_database):
    _, session_factory = history_database
    first_user_id = _create_user(session_factory, "first")
    second_user_id = _create_user(session_factory, "second")
    save_chat_message(first_user_id, _chat_result("First question"), session_factory)
    save_chat_message(second_user_id, _chat_result("Second question"), session_factory)

    first_history = get_user_chat_history(first_user_id, session_factory)
    second_history = get_user_chat_history(second_user_id, session_factory)

    assert [item["question"] for item in first_history] == ["First question"]
    assert [item["question"] for item in second_history] == ["Second question"]


def test_history_is_newest_first_and_supports_default_and_custom_limits(history_database):
    _, session_factory = history_database
    user_id = _create_user(session_factory, "student")
    for index in range(55):
        save_chat_message(
            user_id, _chat_result(f"Question {index}", f"Answer {index}"), session_factory
        )

    default_history = get_user_chat_history(user_id, session_factory)
    custom_history = get_user_chat_history(user_id, session_factory, limit=3)

    assert DEFAULT_HISTORY_LIMIT == 50
    assert len(default_history) == 50
    assert default_history[0]["question"] == "Question 54"
    assert default_history[-1]["question"] == "Question 5"
    assert [item["question"] for item in custom_history] == [
        "Question 54",
        "Question 53",
        "Question 52",
    ]


@pytest.mark.parametrize("value", ["", "0", "101", "-1", "1.5", "all", " 2"])
def test_history_limit_rejects_invalid_values(value):
    with pytest.raises(ChatHistoryLimitError):
        parse_history_limit(value)


def test_history_limit_defaults_and_accepts_supported_values():
    assert parse_history_limit(None) == 50
    assert parse_history_limit("1") == 1
    assert parse_history_limit("100") == 100


def test_chat_service_persists_only_successful_graph_responses(history_database):
    _, session_factory = history_database
    user_id = _create_user(session_factory, "student")

    class FakeGraph:
        def invoke(self, state):
            return {
                **_chat_result(state["question"], "Graph answer"),
                "analyzed_query": state["question"],
            }

    service = AcademicChatService(graph_factory=FakeGraph)
    response, saved = service.answer_for_user(
        {"question": "What is polymorphism?"}, user_id, session_factory
    )

    with session_factory() as session:
        messages = session.scalars(select(ChatMessage)).all()
    assert saved is True
    assert response["answer"] == "Graph answer"
    assert len(messages) == 1
    assert messages[0].user_id == user_id


def test_failed_graph_does_not_create_history(history_database):
    _, session_factory = history_database
    user_id = _create_user(session_factory, "student")

    class FailingGraph:
        def invoke(self, state):
            raise RuntimeError("graph failed")

    service = AcademicChatService(graph_factory=FailingGraph)
    with pytest.raises(ChatGraphError):
        service.answer_for_user({"question": "Question"}, user_id, session_factory)

    with session_factory() as session:
        assert session.scalar(select(ChatMessage.id)) is None


def test_chat_response_survives_recoverable_history_database_error(history_database):
    _, session_factory = history_database
    user_id = _create_user(session_factory, "student")

    class FakeGraph:
        def invoke(self, state):
            return {**_chat_result(state["question"]), "analyzed_query": state["question"]}

    def broken_session_factory():
        raise OperationalError("session", {}, RuntimeError("database unavailable"))

    service = AcademicChatService(graph_factory=FakeGraph)
    response, saved = service.answer_for_user(
        {"question": "Question"}, user_id, broken_session_factory
    )

    assert saved is False
    assert response["answer"] == "Answer"
    assert get_user_chat_history(user_id, session_factory) == []
