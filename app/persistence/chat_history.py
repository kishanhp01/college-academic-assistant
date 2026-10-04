from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.database import ChatMessage


DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 100


class ChatHistoryError(RuntimeError):
    """Raised when chat history cannot be read or saved."""


class ChatHistoryLimitError(ValueError):
    """Raised when a requested history limit is outside the supported range."""


def parse_history_limit(value: str | None) -> int:
    """Parse the optional URL limit without accepting arbitrary query expressions."""
    if value is None:
        return DEFAULT_HISTORY_LIMIT
    if not value.isascii() or not value.isdecimal():
        raise ChatHistoryLimitError("Limit must be a whole number from 1 to 100.")

    limit = int(value)
    if not 1 <= limit <= MAX_HISTORY_LIMIT:
        raise ChatHistoryLimitError("Limit must be a whole number from 1 to 100.")
    return limit


def _serialize_message(message: ChatMessage) -> dict[str, Any]:
    created_at: datetime = message.created_at
    return {
        "id": message.id,
        "question": message.question,
        "answer": message.answer,
        "route": message.route,
        "source": message.source,
        "created_at": created_at.isoformat(),
    }


def save_chat_message(
    user_id: int,
    chat_result: dict[str, Any],
    session_factory: sessionmaker[Session],
) -> dict[str, Any]:
    """Persist a successful graph result for its authenticated user."""
    question = chat_result.get("question")
    answer = chat_result.get("answer")
    route = chat_result.get("route")
    source = chat_result.get("source")
    if (
        type(user_id) is not int
        or user_id < 1
        or not isinstance(question, str)
        or not isinstance(answer, str)
        or (route is not None and not isinstance(route, str))
        or (source is not None and not isinstance(source, str))
    ):
        raise ValueError("Chat result does not contain valid history fields.")

    try:
        with session_factory() as session:
            message = ChatMessage(
                user_id=user_id,
                question=question,
                answer=answer,
                route=route,
                source=source,
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return _serialize_message(message)
    except SQLAlchemyError:
        raise ChatHistoryError("Chat history could not be saved.") from None


def get_user_chat_history(
    user_id: int,
    session_factory: sessionmaker[Session],
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    """Return only the requested user's recent public chat records."""
    if type(user_id) is not int or user_id < 1:
        raise ValueError("A valid user ID is required.")
    if type(limit) is not int or not 1 <= limit <= MAX_HISTORY_LIMIT:
        raise ChatHistoryLimitError("Limit must be a whole number from 1 to 100.")

    try:
        with session_factory() as session:
            messages = session.scalars(
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(limit)
            ).all()
            return [_serialize_message(message) for message in messages]
    except SQLAlchemyError:
        raise ChatHistoryError("Chat history could not be loaded.") from None
