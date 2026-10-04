import pytest

from app.api.auth_service import authenticate_user, get_user_by_id
from app.configuration.settings import get_settings
from app.persistence.database import User, create_session_factory, hash_password, initialize_database


@pytest.fixture
def auth_session_factory():
    engine = initialize_database("sqlite:///:memory:")
    yield create_session_factory(engine)
    engine.dispose()


@pytest.fixture
def registered_user(auth_session_factory):
    with auth_session_factory() as session:
        user = User(
            username="student",
            email="student@example.com",
            password_hash=hash_password("password123"),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
    return auth_session_factory, user_id


def test_authenticate_user_accepts_password_and_normalizes_email(registered_user):
    session_factory, user_id = registered_user

    user = authenticate_user(
        {"email": " Student@Example.COM ", "password": "password123"}, session_factory
    )

    assert user == {"id": user_id, "username": "student", "email": "student@example.com"}
    assert "password_hash" not in user


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "student@example.com", "password": "wrongpassword"},
        {"email": "unknown@example.com", "password": "password123"},
        {"email": "not-an-email", "password": "password123"},
        {"email": "student@example.com", "password": " "},
        None,
    ],
)
def test_invalid_credentials_return_same_result(registered_user, credentials):
    session_factory, _ = registered_user

    assert authenticate_user(credentials, session_factory) is None


def test_get_user_by_id_returns_only_public_identity(registered_user):
    session_factory, user_id = registered_user

    assert get_user_by_id(user_id, session_factory) == {
        "id": user_id,
        "username": "student",
        "email": "student@example.com",
    }
    assert get_user_by_id(999, session_factory) is None


def test_session_settings_are_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-only-secret-placeholder")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    get_settings.cache_clear()

    try:
        settings = get_settings()
        assert settings.flask_secret_key == "test-only-secret-placeholder"
        assert settings.session_cookie_secure is True
    finally:
        get_settings.cache_clear()
