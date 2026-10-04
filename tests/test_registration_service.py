import pytest
from sqlalchemy import select

from app.api.auth_service import (
    DuplicateUserError,
    RegistrationValidationError,
    register_user,
)
from app.persistence.database import User, create_session_factory, initialize_database


@pytest.fixture
def registration_database():
    engine = initialize_database("sqlite:///:memory:")
    yield create_session_factory(engine)
    engine.dispose()


def test_register_user_normalizes_email_and_returns_safe_user(registration_database):
    password = "password123"

    result = register_user(
        {"username": " student ", "email": "Student@Example.COM", "password": password},
        registration_database,
    )

    assert result == {"id": 1, "username": "student", "email": "student@example.com"}
    assert "password" not in result
    assert "password_hash" not in result
    with registration_database() as session:
        user = session.scalar(select(User).where(User.id == result["id"]))
        assert user is not None
        assert user.password_hash != password


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"username": " ", "email": "student@example.com", "password": "password123"},
        {"username": "student", "email": "  ", "password": "password123"},
        {"username": "student", "email": "student@example.com", "password": " \t "},
        {"username": "student", "email": "not-an-email", "password": "password123"},
        {"username": "student", "email": "student@example.com", "password": "short"},
    ],
)
def test_invalid_registration_data_is_rejected(registration_database, payload):
    with pytest.raises(RegistrationValidationError):
        register_user(payload, registration_database)


def test_duplicate_username_is_rejected(registration_database):
    register_user(
        {"username": "student", "email": "first@example.com", "password": "password123"},
        registration_database,
    )

    with pytest.raises(DuplicateUserError, match="Username"):
        register_user(
            {"username": "student", "email": "second@example.com", "password": "password123"},
            registration_database,
        )


def test_duplicate_normalized_email_is_rejected(registration_database):
    register_user(
        {"username": "first", "email": "student@example.com", "password": "password123"},
        registration_database,
    )

    with pytest.raises(DuplicateUserError, match="Email"):
        register_user(
            {"username": "second", "email": " Student@Example.COM ", "password": "password123"},
            registration_database,
        )
