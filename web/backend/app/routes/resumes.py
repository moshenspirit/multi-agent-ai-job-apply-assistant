"""
简历管理 API 路由
"""
import os
import json
import uuid
from flask import Blueprint, jsonify, request

from app.database import SessionLocal
from app.models.resume import Resume
from app.services.resume_parser import extract_text_from_file, parse_resume_to_structured

bp = Blueprint("resumes", __name__, url_prefix="/api/resumes")

# 上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data", "resumes")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@bp.route("", methods=["GET"])
def list_resumes():
    """获取所有简历"""
    db = SessionLocal()
    try:
        resumes = db.query(Resume).all()
        return jsonify([r.to_dict() for r in resumes])
    finally:
        db.close()


@bp.route("/<int:resume_id>", methods=["GET"])
def get_resume(resume_id: int):
    """获取单个简历"""
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return jsonify({"error": "简历不存在"}), 404
        return jsonify(resume.to_dict())
    finally:
        db.close()


@bp.route("/upload", methods=["POST"])
def upload_resume():
    """上传并解析简历文件"""
    if "file" not in request.files:
        return jsonify({"error": "未选择文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名为空"}), 400

    # 获取方向参数
    direction = request.form.get("direction", "frontend")
    if direction not in ("frontend", "ai"):
        return jsonify({"error": "方向参数无效，应为 frontend 或 ai"}), 400

    # 获取简历名称
    name = request.form.get("name", os.path.splitext(file.filename)[0])

    # 检查文件格式
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if ext not in allowed:
        return jsonify({"error": f"不支持的文件格式: {ext}，支持: {', '.join(allowed)}"}), 400

    # 保存文件
    _ensure_upload_dir()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    file.save(file_path)

    # 提取文本
    try:
        raw_text = extract_text_from_file(file_path)
    except ImportError as e:
        os.remove(file_path)  # 清理文件
        return jsonify({"error": f"解析依赖缺失: {str(e)}"}), 500
    except Exception as e:
        os.remove(file_path)
        return jsonify({"error": f"文本提取失败: {str(e)}"}), 500

    if not raw_text.strip():
        os.remove(file_path)
        return jsonify({"error": "未能从文件中提取到文本内容，请检查文件是否清晰可读"}), 400

    # LLM 结构化提取
    try:
        structured_data = parse_resume_to_structured(raw_text)
    except Exception as e:
        structured_data = {
            "name": "",
            "skills": [],
            "years": 0,
            "education": "",
            "school": "",
            "projects": [],
            "raw_summary": raw_text[:500],
            "parse_error": str(e),
        }

    structured_json = json.dumps(structured_data, ensure_ascii=False)

    # 存入数据库
    db = SessionLocal()
    try:
        resume = Resume(
            name=name,
            direction=direction,
            file_path=file_path,
            raw_text=raw_text,
            structured=structured_json,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return jsonify(resume.to_dict()), 201
    except Exception as e:
        db.rollback()
        os.remove(file_path)
        return jsonify({"error": f"数据库写入失败: {str(e)}"}), 500
    finally:
        db.close()


@bp.route("/<int:resume_id>", methods=["PUT"])
def update_resume(resume_id: int):
    """更新简历信息"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return jsonify({"error": "简历不存在"}), 404

        # 允许更新的字段
        for key in ("name", "direction"):
            if key in data:
                setattr(resume, key, data[key])

        # structured 支持部分更新
        if "structured" in data:
            if isinstance(data["structured"], str):
                resume.structured = data["structured"]
            else:
                resume.structured = json.dumps(data["structured"], ensure_ascii=False)

        db.commit()
        return jsonify(resume.to_dict())
    finally:
        db.close()


@bp.route("/<int:resume_id>", methods=["DELETE"])
def delete_resume(resume_id: int):
    """删除简历"""
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return jsonify({"error": "简历不存在"}), 404

        # 删除文件
        if resume.file_path and os.path.exists(resume.file_path):
            try:
                os.remove(resume.file_path)
            except OSError:
                pass

        db.delete(resume)
        db.commit()
        return jsonify({"message": "删除成功"})
    finally:
        db.close()


@bp.route("/<int:resume_id>/parse", methods=["POST"])
def reparse_resume(resume_id: int):
    """重新解析简历"""
    db = SessionLocal()
    try:
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            return jsonify({"error": "简历不存在"}), 404

        if not resume.file_path or not os.path.exists(resume.file_path):
            return jsonify({"error": "简历文件不存在"}), 404

        # 重新提取文本
        raw_text = extract_text_from_file(resume.file_path)
        if not raw_text.strip():
            return jsonify({"error": "文本提取失败"}), 400

        # 重新结构化
        structured_data = parse_resume_to_structured(raw_text)
        resume.raw_text = raw_text
        resume.structured = json.dumps(structured_data, ensure_ascii=False)

        db.commit()
        return jsonify(resume.to_dict())
    finally:
        db.close()
