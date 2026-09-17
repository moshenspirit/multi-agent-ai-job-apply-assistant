"""
配置管理 API 路由
"""
import json
from flask import Blueprint, jsonify, request

from app.database import SessionLocal
from app.models.config_model import ConfigModel

bp = Blueprint("config", __name__, url_prefix="/api/config")


def _get_or_create_config(db):
    """获取或创建配置（单例）"""
    config = db.query(ConfigModel).filter(ConfigModel.id == 1).first()
    if not config:
        config = ConfigModel(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@bp.route("", methods=["GET"])
def get_config():
    """获取当前配置"""
    db = SessionLocal()
    try:
        config = _get_or_create_config(db)
        return jsonify(config.to_dict())
    finally:
        db.close()


@bp.route("", methods=["PUT"])
def update_config():
    """更新配置"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    db = SessionLocal()
    try:
        config = _get_or_create_config(db)

        if "search_keywords" in data:
            config.search_keywords = json.dumps(data["search_keywords"], ensure_ascii=False)
        if "filter_conditions" in data:
            config.filter_conditions = json.dumps(data["filter_conditions"], ensure_ascii=False)
        if "weights" in data:
            config.weights = json.dumps(data["weights"], ensure_ascii=False)
        if "max_pages" in data:
            config.max_pages = data["max_pages"]
        if "max_collect_time" in data:
            config.max_collect_time = data["max_collect_time"]

        db.commit()
        return jsonify(config.to_dict())
    finally:
        db.close()
