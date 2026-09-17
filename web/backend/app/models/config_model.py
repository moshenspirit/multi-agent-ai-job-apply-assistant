"""
配置数据模型（单例表，只有 id=1 一条记录）
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class ConfigModel(Base):
    __tablename__ = "config"

    id = Column(Integer, primary_key=True)

    # JSON 格式存储
    search_keywords = Column(Text, nullable=False, default="[]")
    filter_conditions = Column(Text, nullable=False, default="{}")
    weights = Column(Text, nullable=False, default="{}")

    # 采集参数
    max_pages = Column(Integer, default=5)
    max_collect_time = Column(Integer, default=600)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "search_keywords": json.loads(self.search_keywords) if self.search_keywords else [],
            "filter_conditions": json.loads(self.filter_conditions) if self.filter_conditions else {},
            "weights": json.loads(self.weights) if self.weights else {},
            "max_pages": self.max_pages,
            "max_collect_time": self.max_collect_time,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
