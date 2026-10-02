from flask import Blueprint, jsonify


api_blueprint = Blueprint("api", __name__, url_prefix="/api")


@api_blueprint.get("/health")
def health_check():
    return jsonify(status="ok")
