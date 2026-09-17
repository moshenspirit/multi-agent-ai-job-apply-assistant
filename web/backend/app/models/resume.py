"""
简历数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    direction = Column(String(50), nullable=False)  # frontend / ai
    file_path = Column(String(500), nullable=True)
    raw_text = Column(Text, nullable=True)
    structured = Column(Text, nullable=True)  # JSON 字符串

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "direction": self.direction,
            "file_path": self.file_path,
            "raw_text": self.raw_text,
            "structured": self.structured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
