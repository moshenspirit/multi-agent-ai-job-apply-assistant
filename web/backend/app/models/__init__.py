"""
数据模型包
"""
from app.models.job import Job
from app.models.resume import Resume
from app.models.config_model import ConfigModel
from app.models.record import DeliveryRecord
from app.models.agent_config import AgentConfig

__all__ = ["Job", "Resume", "ConfigModel", "DeliveryRecord", "AgentConfig"]
