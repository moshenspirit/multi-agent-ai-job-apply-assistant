"""
投递记录数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class DeliveryRecord(Base):
    __tablename__ = "delivery_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String(20), default="applied")  # applied / interviewed / offer / rejected
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", backref="delivery_records")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "status": self.status,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
