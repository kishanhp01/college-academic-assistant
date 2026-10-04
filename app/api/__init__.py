"""Flask API package."""


def create_app(config: dict[str, object] | None = None):
    """Load the Flask factory only when it is requested."""
    from app.api.app import create_app as flask_create_app

    return flask_create_app(config)

__all__ = ["create_app"]
