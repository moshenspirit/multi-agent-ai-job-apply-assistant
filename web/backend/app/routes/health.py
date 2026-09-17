"""
健康检查路由
"""
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "boss-job-matcher",
        "version": "1.0.0",
    })
