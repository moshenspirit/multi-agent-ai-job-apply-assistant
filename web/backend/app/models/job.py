"""
岗位数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    # ---- 基本信息 ----
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(200), nullable=False)
    company_name = Column(String(200), nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    city = Column(String(50), nullable=True)
    district = Column(String(50), nullable=True)
    experience = Column(String(50), nullable=True)
    education = Column(String(50), nullable=True)

    # ---- 岗位详情 ----
    jd_text = Column(Text, nullable=True)
    company_size = Column(String(50), nullable=True)
    company_industry = Column(String(100), nullable=True)
    company_finance = Column(String(50), nullable=True)
    boss_active = Column(String(50), nullable=True)

    # ---- 来源 ----
    source_url = Column(String(500), unique=True, nullable=False)
    source_keyword = Column(String(100), nullable=True)

    # ---- 匹配结果 ----
    match_direction = Column(String(20), nullable=True)  # frontend / ai / both / none
    match_score_frontend = Column(Integer, nullable=True)
    match_score_ai = Column(Integer, nullable=True)
    match_reason = Column(Text, nullable=True)

    # ---- 状态 ----
    status = Column(String(20), default="new")  # new / viewed / applied / ignored
    collect_batch = Column(String(50), nullable=True)

    # ---- 公司避坑（2026-08-26 加）----
    company_profile = Column(Text, nullable=True)      # 公司信息包（被动形态：人工问坑用）
    risk_flags = Column(Text, nullable=True)          # JSON 数组，DeepSeek 主动分析输出
    risk_analyzed_at = Column(DateTime, nullable=True)  # 上次主动分析时间

    # ---- 时间戳 ----
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_name": self.job_name,
            "company_name": self.company_name,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "city": self.city,
            "district": self.district,
            "experience": self.experience,
            "education": self.education,
            "jd_text": self.jd_text,
            "company_size": self.company_size,
            "company_industry": self.company_industry,
            "company_finance": self.company_finance,
            "boss_active": self.boss_active,
            "source_url": self.source_url,
            "source_keyword": self.source_keyword,
            "match_direction": self.match_direction,
            "match_score_frontend": self.match_score_frontend,
            "match_score_ai": self.match_score_ai,
            "match_reason": self.match_reason,
            "status": self.status,
            "collect_batch": self.collect_batch,
            "company_profile": self.company_profile,
            "risk_flags": self.risk_flags,
            "risk_analyzed_at": self.risk_analyzed_at.isoformat() if self.risk_analyzed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
