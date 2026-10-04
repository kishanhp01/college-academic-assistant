import hashlib
import hmac
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    func,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.configuration.settings import get_settings

_PASSWORD_HASH_ITERATIONS = 600_000


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    user: Mapped[User] = relationship(back_populates="chat_messages")


def hash_password(password: str) -> str:
    """Create a salted PBKDF2 hash suitable for storing instead of a password."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_HASH_ITERATIONS
    )
    return f"pbkdf2_sha256${_PASSWORD_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a hash created by :func:`hash_password`."""
    try:
        scheme, iterations_text, salt_text, digest_text = stored_hash.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected_digest = bytes.fromhex(digest_text)
        if (
            scheme != "pbkdf2_sha256"
            or not 1 <= iterations <= 2_000_000
            or len(salt) != 16
            or len(expected_digest) != 32
        ):
            return False
    except (AttributeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create an engine and make the parent folder for a file-backed SQLite URL."""
    url = make_url(database_url or get_settings().database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        database_path = Path(url.database)
        if database_path.parent != Path("."):
            database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _connection_record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def initialize_database(database_url: str | None = None) -> Engine:
    """Create database tables and return the engine used to access them."""
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Build a session factory for an existing engine or the configured database."""
    return sessionmaker(bind=engine or create_database_engine(), expire_on_commit=False)
