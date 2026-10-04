from threading import RLock
from typing import Any, Callable

from sqlalchemy.orm import Session, sessionmaker

from app.persistence.chat_history import ChatHistoryError, save_chat_message

MAX_QUESTION_LENGTH = 4_000


class ChatRequestError(ValueError):
    """Raised when a chat request does not contain a usable question."""


class KnowledgeIndexUnavailableError(RuntimeError):
    """Raised when a college question cannot be answered because the index is absent."""


class AssistantConfigurationError(RuntimeError):
    """Raised when the configured assistant provider cannot be used."""


class ChatGraphError(RuntimeError):
    """Raised when the academic graph fails for an unexpected reason."""

    def __init__(self, diagnostic_type: str):
        super().__init__("The academic assistant could not process the request.")
        self.diagnostic_type = diagnostic_type


def validate_question_payload(payload: Any) -> str:
    """Validate JSON chat input and return a trimmed, bounded question."""
    if not isinstance(payload, dict):
        raise ChatRequestError("A JSON object is required.")

    question = payload.get("question")
    if not isinstance(question, str):
        raise ChatRequestError("Question must be a string.")

    question = question.strip()
    if not question:
        raise ChatRequestError("Question cannot be empty.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ChatRequestError(
            f"Question must be {MAX_QUESTION_LENGTH} characters or fewer."
        )
    return question


def _serialize_source(source: Any) -> str | dict[str, str | int] | None:
    """Keep only small, useful JSON fields; ignore complex objects such as Documents."""
    if isinstance(source, str):
        return source[:1_000]
    if not isinstance(source, dict):
        return None

    safe_source: dict[str, str | int] = {}
    for key in ("label", "source", "page", "excerpt"):
        value = source.get(key)
        if isinstance(value, str):
            safe_source[key] = value[:1_000]
        elif key == "page" and isinstance(value, int) and not isinstance(value, bool):
            safe_source[key] = value
    return safe_source or None


def serialize_graph_result(result: Any, question: str) -> dict[str, Any]:
    """Return only the student-facing fields from a LangGraph result."""
    if not isinstance(result, dict) or not isinstance(result.get("answer"), str):
        raise ChatGraphError("invalid_result")

    route = result.get("route")
    if route not in ("college", "general"):
        raise ChatGraphError("invalid_result")

    raw_sources = result.get("sources", [])
    if not isinstance(raw_sources, (list, tuple)):
        raw_sources = []
    sources = [
        safe_source
        for item in raw_sources
        if (safe_source := _serialize_source(item)) is not None
    ]

    analyzed_query = result.get("analyzed_query")
    source_name = result.get("source")
    return {
        "answer": result["answer"],
        "question": question,
        "analyzed_query": analyzed_query if isinstance(analyzed_query, str) else question,
        "route": route,
        "source": source_name if isinstance(source_name, str) else (
            "college_documents" if route == "college" else "general_llm"
        ),
        "sources": sources,
    }


def _build_academic_graph():
    from app.workflows.academic import build_academic_graph

    return build_academic_graph()


class AcademicChatService:
    """Reuse one compiled graph per Flask app while serializing its mutable first use."""

    def __init__(self, graph_factory: Callable[[], Any] | None = None):
        self._graph_factory = graph_factory or _build_academic_graph
        self._graph: Any | None = None
        self._lock = RLock()

    def answer(self, payload: Any) -> dict[str, Any]:
        question = validate_question_payload(payload)

        # The graph lazily creates and stores its retriever, so serialize invocations
        # on this app-scoped service to avoid concurrent initialization races.
        with self._lock:
            try:
                if self._graph is None:
                    self._graph = self._graph_factory()
                result = self._graph.invoke({"question": question})
            except FileNotFoundError:
                raise KnowledgeIndexUnavailableError(
                    "The college knowledge index is unavailable."
                ) from None
            except ValueError:
                raise AssistantConfigurationError(
                    "The academic assistant is not configured correctly."
                ) from None
            except Exception as error:
                raise ChatGraphError(type(error).__name__) from None

        return serialize_graph_result(result, question)

    def answer_for_user(
        self,
        payload: Any,
        user_id: int,
        session_factory: sessionmaker[Session],
    ) -> tuple[dict[str, Any], bool]:
        """Answer first, then best-effort save the successful response for its user."""
        result = self.answer(payload)
        try:
            save_chat_message(user_id, result, session_factory)
        except ChatHistoryError:
            return result, False
        return result, True
