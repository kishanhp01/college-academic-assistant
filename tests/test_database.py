import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.configuration.settings import get_settings
from app.persistence.database import (
    User,
    create_session_factory,
    hash_password,
    initialize_database,
)


@pytest.fixture
def database_engine():
    engine = initialize_database("sqlite:///:memory:")
    yield engine
    engine.dispose()


def test_database_initialization_creates_user_table(database_engine):
    table_names = inspect(database_engine).get_table_names()
    assert "users" in table_names
    assert "chat_messages" in table_names


def test_user_creation_stores_password_hash_and_created_at(database_engine):
    session_factory = create_session_factory(database_engine)
    plaintext_password = "a test password"
    password_hash = hash_password(plaintext_password)

    with session_factory() as session:
        user = User(
            username="student1",
            email="student1@example.test",
            password_hash=password_hash,
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.password_hash == password_hash
        assert user.password_hash != plaintext_password
        assert user.created_at is not None


def test_duplicate_username_is_rejected(database_engine):
    session_factory = create_session_factory(database_engine)
    password_hash = hash_password("password")

    with session_factory() as session:
        session.add_all(
            [
                User(username="same", email="first@example.test", password_hash=password_hash),
                User(username="same", email="second@example.test", password_hash=password_hash),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_duplicate_email_is_rejected(database_engine):
    session_factory = create_session_factory(database_engine)
    password_hash = hash_password("password")

    with session_factory() as session:
        session.add_all(
            [
                User(username="first", email="same@example.test", password_hash=password_hash),
                User(username="second", email="same@example.test", password_hash=password_hash),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_database_url_uses_pydantic_settings_environment(monkeypatch):
    configured_url = "sqlite:///:memory:"
    monkeypatch.setenv("DATABASE_URL", configured_url)
    get_settings.cache_clear()

    try:
        assert get_settings().database_url == configured_url
    finally:
        get_settings.cache_clear()
