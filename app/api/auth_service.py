import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.persistence.database import User, hash_password, verify_password


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegistrationValidationError(ValueError):
    """Raised when registration input is incomplete or invalid."""


class DuplicateUserError(ValueError):
    """Raised when the username or email already belongs to another user."""


class RegistrationDatabaseError(RuntimeError):
    """Raised when registration cannot be saved because of a database error."""


class AuthenticationDatabaseError(RuntimeError):
    """Raised when authentication cannot read the database safely."""


def normalize_email(value: Any) -> str | None:
    """Trim and lowercase a valid email address, or return None for invalid input."""
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if len(email) > 255 or not _EMAIL_PATTERN.fullmatch(email):
        return None
    return email


def _public_user(user: User) -> dict[str, object]:
    return {"id": user.id, "username": user.username, "email": user.email}


def _validate_registration(payload: Any) -> tuple[str, str, str]:
    if not isinstance(payload, dict):
        raise RegistrationValidationError("A JSON object is required.")

    values: dict[str, str] = {}
    for field in ("username", "email", "password"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise RegistrationValidationError(f"{field.capitalize()} is required.")
        values[field] = value

    username = values["username"].strip()
    email = normalize_email(values["email"])
    password = values["password"]

    if len(username) > 80:
        raise RegistrationValidationError("Username must be 80 characters or fewer.")
    if email is None:
        raise RegistrationValidationError("Enter a valid email address.")
    if len(password) < 8:
        raise RegistrationValidationError("Password must be at least 8 characters long.")

    return username, email, password


def authenticate_user(
    payload: Any, session_factory: sessionmaker[Session]
) -> dict[str, object] | None:
    """Return safe user details for valid credentials, otherwise None."""
    if not isinstance(payload, dict):
        return None

    email = normalize_email(payload.get("email"))
    password = payload.get("password")
    if email is None or not isinstance(password, str) or not password.strip():
        return None

    try:
        with session_factory() as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None or not verify_password(password, user.password_hash):
                return None
            return _public_user(user)
    except SQLAlchemyError:
        raise AuthenticationDatabaseError("Authentication is temporarily unavailable.") from None


def get_user_by_id(
    user_id: int, session_factory: sessionmaker[Session]
) -> dict[str, object] | None:
    """Return safe user details for a valid ID, or None if the account is absent."""
    try:
        with session_factory() as session:
            user = session.get(User, user_id)
            return _public_user(user) if user is not None else None
    except SQLAlchemyError:
        raise AuthenticationDatabaseError("Authentication is temporarily unavailable.") from None


def register_user(payload: Any, session_factory: sessionmaker[Session]) -> dict[str, object]:
    """Validate registration data and save a user without exposing password fields."""
    username, email, password = _validate_registration(payload)

    try:
        with session_factory() as session:
            if session.scalar(select(User.id).where(User.username == username)):
                raise DuplicateUserError("Username is already registered.")
            if session.scalar(select(User.id).where(User.email == email)):
                raise DuplicateUserError("Email is already registered.")

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return {"id": user.id, "username": user.username, "email": user.email}
    except DuplicateUserError:
        raise
    except IntegrityError:
        try:
            with session_factory() as session:
                if session.scalar(select(User.id).where(User.username == username)):
                    raise DuplicateUserError("Username is already registered.")
                if session.scalar(select(User.id).where(User.email == email)):
                    raise DuplicateUserError("Email is already registered.")
        except DuplicateUserError:
            raise
        except SQLAlchemyError:
            pass
        raise RegistrationDatabaseError("Registration could not be saved.") from None
    except SQLAlchemyError:
        raise RegistrationDatabaseError("Registration could not be saved.") from None
