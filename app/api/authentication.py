from functools import wraps
from typing import Any, Callable

from flask import current_app, g, jsonify, session

from app.api.auth_service import AuthenticationDatabaseError, get_user_by_id


def require_auth(view: Callable[..., Any]) -> Callable[..., Any]:
    """Require a valid signed-in user for a Flask route."""
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        user_id = session.get("user_id")
        if type(user_id) is not int or user_id < 1:
            return jsonify(error="Authentication required."), 401

        try:
            user = get_user_by_id(
                user_id, current_app.extensions["database_session_factory"]
            )
        except AuthenticationDatabaseError:
            current_app.logger.error("Database error while checking authentication")
            return jsonify(error="Authentication is temporarily unavailable."), 500

        if user is None:
            session.clear()
            return jsonify(error="Authentication required."), 401

        g.current_user = user
        return view(*args, **kwargs)

    return wrapped
