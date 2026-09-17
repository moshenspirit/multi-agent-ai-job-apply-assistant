"""
Agent 配置数据模型（Agent 管理界面的配置持久化）
"""
import json
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime

from app.database import Base


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    name = Column(String(50), primary_key=True)          # collector / matcher / skirmish
    config_json = Column(Text, nullable=False, default="{}")  # JSON 字符串
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        try:
            config = json.loads(self.config_json or "{}")
        except (ValueError, TypeError):
            config = {}
        return {
            "name": self.name,
            "config": config,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
