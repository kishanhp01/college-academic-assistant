from flask import Flask

from app.api.routes import api_blueprint


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.register_blueprint(api_blueprint)
    return app
