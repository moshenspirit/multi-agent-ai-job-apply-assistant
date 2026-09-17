"""
数据库初始化模块
SQLAlchemy ORM 引擎和会话管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import Config

# 确保 data 目录存在
db_path = Config.DATABASE_URL.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(os.path.join(os.path.dirname(__file__), "..", db_dir), exist_ok=True)

# 创建引擎（SQLite 需要 check_same_thread=False）
engine = create_engine(
    Config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=Config.FLASK_DEBUG,
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()


def init_db():
    """创建所有表（如果不存在）"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
