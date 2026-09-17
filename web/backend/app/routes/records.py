"""
投递记录 API 路由（需求 7：状态流转 + 去重 + 岗位信息 join）
"""
from flask import Blueprint, jsonify, request

from app.database import SessionLocal
from app.models.record import DeliveryRecord
from app.models.job import Job

bp = Blueprint("records", __name__, url_prefix="/api/records")

VALID_STATUS = ("applied", "interviewed", "offer", "rejected")


def _record_with_job(record: DeliveryRecord) -> dict:
    """记录 + 关联岗位信息（列表/详情展示用）"""
    d = record.to_dict()
    if record.job:
        d["job_name"] = record.job.job_name
        d["company_name"] = record.job.company_name
        d["salary_min"] = record.job.salary_min
        d["salary_max"] = record.job.salary_max
    else:
        d["job_name"] = None
        d["company_name"] = None
        d["salary_min"] = None
        d["salary_max"] = None
    return d


@bp.route("", methods=["GET"])
def list_records():
    """获取投递记录列表（含岗位名/公司/薪资）"""
    db = SessionLocal()
    try:
        job_id = request.args.get("job_id", type=int)
        query = db.query(DeliveryRecord)
        if job_id:
            query = query.filter(DeliveryRecord.job_id == job_id)
        records = query.order_by(DeliveryRecord.created_at.desc()).all()
        return jsonify([_record_with_job(r) for r in records])
    finally:
        db.close()


@bp.route("", methods=["POST"])
def create_record():
    """新增投递记录（幂等去重：同一岗位重复投递返回已有记录）"""
    data = request.get_json()
    if not data or "job_id" not in data:
        return jsonify({"error": "缺少 job_id"}), 400

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == data["job_id"]).first()
        if not job:
            return jsonify({"error": "岗位不存在"}), 404

        # 去重：同一岗位已有投递记录 → 幂等返回（不重复建）
        existing = (
            db.query(DeliveryRecord)
            .filter(DeliveryRecord.job_id == data["job_id"])
            .first()
        )
        if existing:
            return jsonify(_record_with_job(existing)), 200

        status = data.get("status", "applied")
        if status not in VALID_STATUS:
            return jsonify({"error": f"无效状态: {status}"}), 400

        record = DeliveryRecord(
            job_id=data["job_id"],
            status=status,
            note=data.get("note"),
        )
        job.status = "applied"  # 同步岗位状态

        db.add(record)
        db.commit()
        db.refresh(record)
        return jsonify(_record_with_job(record)), 201
    finally:
        db.close()


@bp.route("/<int:record_id>/status", methods=["PUT"])
def update_record_status(record_id: int):
    """更新投递状态（已投递 → 面试中 → 已录用/未通过）"""
    data = request.get_json()
    new_status = data.get("status") if data else None
    if new_status not in VALID_STATUS:
        return jsonify({"error": f"无效状态: {new_status}，可选 {list(VALID_STATUS)}"}), 400

    db = SessionLocal()
    try:
        record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
        if not record:
            return jsonify({"error": "记录不存在"}), 404
        record.status = new_status
        db.commit()
        db.refresh(record)
        return jsonify(_record_with_job(record))
    finally:
        db.close()


@bp.route("/<int:record_id>", methods=["DELETE"])
def delete_record(record_id: int):
    """删除投递记录"""
    db = SessionLocal()
    try:
        record = db.query(DeliveryRecord).filter(DeliveryRecord.id == record_id).first()
        if not record:
            return jsonify({"error": "记录不存在"}), 404
        db.delete(record)
        db.commit()
        return jsonify({"message": "删除成功"})
    finally:
        db.close()
