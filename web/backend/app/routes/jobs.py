"""
岗位相关 API 路由
"""
import csv
import io
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import desc, func

from app.database import SessionLocal
from app.models.job import Job

bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

# 允许排序的列白名单（2026-09-03：非法 sort_by 直接 400，避免静默回落/异常字段）
SORTABLE_COLUMNS = {"id", "created_at", "updated_at", "salary_min", "salary_max", "company_name", "job_name"}

# 岗位状态合法值
VALID_JOB_STATUS = ("new", "viewed", "applied", "ignored")


def _parse_statuses(raw: str | None) -> list[str] | None:
    """解析 status 参数（支持逗号分隔多值，如 status=viewed,applied）。非法值返回 None"""
    if not raw:
        return None
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    if not parts or any(s not in VALID_JOB_STATUS for s in parts):
        return None
    return parts


@bp.route("", methods=["GET"])
def list_jobs():
    """获取岗位列表（支持分页、筛选、排序）"""
    db = SessionLocal()
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        statuses = _parse_statuses(request.args.get("status"))
        if request.args.get("status") and statuses is None:
            return jsonify({"error": f"无效的状态值，可选: {list(VALID_JOB_STATUS)}"}), 400
        match_direction = request.args.get("match_direction")
        sort_by = request.args.get("sort_by", "created_at")
        order = request.args.get("order", "desc")

        if sort_by not in SORTABLE_COLUMNS:
            return jsonify({"error": f"无效的排序字段: {sort_by}"}), 400
        if order not in ("asc", "desc"):
            return jsonify({"error": "order 仅支持 asc / desc"}), 400

        query = db.query(Job)

        # 筛选
        if statuses:
            query = query.filter(Job.status.in_(statuses))
        if match_direction:
            query = query.filter(Job.match_direction == match_direction)

        # 排序
        sort_column = getattr(Job, sort_by, Job.created_at)
        if order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # 分页
        total = query.count()
        jobs = query.offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "data": [j.to_dict() for j in jobs],
            "total": total,
            "page": page,
            "per_page": per_page,
        })
    finally:
        db.close()


@bp.route("/<int:job_id>", methods=["GET"])
def get_job(job_id: int):
    """获取单个岗位详情"""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({"error": "岗位不存在"}), 404
        return jsonify(job.to_dict())
    finally:
        db.close()


@bp.route("/<int:job_id>/status", methods=["PUT"])
def update_job_status(job_id: int):
    """更新岗位状态"""
    data = request.get_json()
    new_status = data.get("status") if data else None
    if new_status not in ("new", "viewed", "applied", "ignored"):
        return jsonify({"error": "无效的状态值"}), 400

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({"error": "岗位不存在"}), 404
        job.status = new_status
        db.commit()
        return jsonify(job.to_dict())
    finally:
        db.close()


@bp.route("/stats", methods=["GET"])
def get_stats():
    """获取统计数据（仪表盘用）"""
    db = SessionLocal()
    try:
        total = db.query(Job).count()
        new_count = db.query(Job).filter(Job.status == "new").count()
        applied_count = db.query(Job).filter(Job.status == "applied").count()
        frontend_match = db.query(Job).filter(Job.match_direction.in_(["frontend", "both"])).count()
        ai_match = db.query(Job).filter(Job.match_direction.in_(["ai", "both"])).count()

        return jsonify({
            "total": total,
            "new": new_count,
            "applied": applied_count,
            "frontend_match": frontend_match,
            "ai_match": ai_match,
        })
    finally:
        db.close()


@bp.route("/company-counts", methods=["GET"])
def company_counts():
    """按公司聚合岗位数（任务④：识别刷屏/批量发帖公司）。返回按数量降序"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Job.company_name, func.count(Job.id))
            .group_by(Job.company_name)
            .order_by(func.count(Job.id).desc())
            .all()
        )
        return jsonify([{"company_name": name, "count": cnt} for name, cnt in rows])
    finally:
        db.close()


# ===== 导出（需求 6 输出层：CSV / Markdown）=====

def _export_query(status: str | None, match_direction: str | None):
    """复用列表筛选逻辑"""
    db = SessionLocal()
    try:
        query = db.query(Job)
        statuses = _parse_statuses(status)
        if statuses:
            query = query.filter(Job.status.in_(statuses))
        if match_direction:
            query = query.filter(Job.match_direction == match_direction)
        return query.order_by(Job.created_at.desc()).all()
    finally:
        db.close()


def _salary_text(job: Job) -> str:
    if job.salary_min or job.salary_max:
        return f"{job.salary_min or '?'}-{job.salary_max or '?'}"
    return "面议"


def _direction_text(job: Job) -> str:
    return {
        "frontend": "前端",
        "ai": "AI",
        "both": "双匹配",
        "none": "不匹配",
    }.get(job.match_direction or "", job.match_direction or "-")


def _status_text(job: Job) -> str:
    return {
        "new": "新采集",
        "viewed": "已查看",
        "applied": "已投递",
        "ignored": "不感兴趣",
    }.get(job.status or "", job.status or "-")


def _risk_text(job: Job) -> str:
    """risk_flags (JSON 数组字符串) → 可读文本"""
    if not job.risk_flags:
        return "未分析"
    try:
        flags = json.loads(job.risk_flags)
    except (ValueError, TypeError):
        return "未分析"
    if not flags:
        return "无明显风险"
    parts = []
    for f in flags:
        sev = f.get("severity", "")
        label = {"high": "高", "mid": "中", "low": "低"}.get(sev, sev)
        reason = f.get("reason", "")
        parts.append(f"[{label}]{reason}")
    return "；".join(parts)


@bp.route("/export", methods=["GET"])
def export_jobs():
    """导出岗位列表（CSV / Markdown），支持与列表相同的筛选参数"""
    fmt = request.args.get("format", "csv")
    status = request.args.get("status")
    match_direction = request.args.get("match_direction")
    if fmt not in ("csv", "md"):
        return jsonify({"error": "format 仅支持 csv / md"}), 400

    jobs = _export_query(status, match_direction)

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "ID", "岗位", "公司", "薪资", "城市", "区域", "经验", "学历",
            "方向", "状态", "公司规模", "行业", "融资", "Boss活跃",
            "风险", "JD", "公司信息包", "原始链接", "采集关键词", "采集批次", "创建时间",
        ])
        for j in jobs:
            writer.writerow([
                j.id, j.job_name, j.company_name, _salary_text(j), j.city or "", j.district or "",
                j.experience or "", j.education or "", _direction_text(j), _status_text(j),
                j.company_size or "", j.company_industry or "", j.company_finance or "", j.boss_active or "",
                _risk_text(j), (j.jd_text or "").replace("\r", " ").replace("\n", " "),
                (j.company_profile or "").replace("\r", " ").replace("\n", " "),
                j.source_url, j.source_keyword or "", j.collect_batch or "",
                j.created_at.strftime("%Y-%m-%d %H:%M") if j.created_at else "",
            ])
        # utf-8-sig（带 BOM）→ Excel 直接打开中文不乱码
        data = buf.getvalue().encode("utf-8-sig")
        filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        mimetype = "text/csv"
    else:
        rows = []
        for i, j in enumerate(jobs, 1):
            rows.append(
                f"| {i} | {j.job_name} | {j.company_name} | {_salary_text(j)} | {j.city or '-'} | "
                f"{j.experience or '-'} | {j.education or '-'} | {_direction_text(j)} | "
                f"{_status_text(j)} | {_risk_text(j)} | [打开]({j.source_url}) |"
            )
        header = "| # | 岗位 | 公司 | 薪资 | 城市 | 经验 | 学历 | 方向 | 状态 | 风险 | 链接 |"
        sep = "|---|------|------|------|------|------|------|------|------|------|------|"
        filter_desc = []
        if status:
            filter_desc.append(f"状态={status}")
        if match_direction:
            filter_desc.append(f"方向={match_direction}")
        md = "\n".join([
            "# AI 投递助手 — 岗位列表",
            "",
            f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 共 {len(jobs)} 条"
            + (f" ｜ 筛选：{'、'.join(filter_desc)}" if filter_desc else ""),
            "",
            header,
            sep,
            *rows,
            "",
        ])
        data = md.encode("utf-8")
        filename = f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        mimetype = "text/markdown"

    return Response(
        data,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
