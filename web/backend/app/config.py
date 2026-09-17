"""
应用配置模块
从 .env 文件和环境变量加载配置
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """全局配置类"""

    # ---- OpenAI ----
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # ---- Flask ----
    FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # ---- 数据库 ----
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/database.db")

    # ---- 文件上传 ----
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "resumes")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # ---- 采集 ----
    COLLECT_MAX_PAGES = 5
    COLLECT_MAX_TIME = 600  # 秒
    COLLECT_DELAY_MIN = 2  # 操作间最小延迟（秒）
    COLLECT_DELAY_MAX = 5  # 操作间最大延迟（秒）
    COLLECT_PAGE_DELAY_MIN = 5
    COLLECT_PAGE_DELAY_MAX = 10
