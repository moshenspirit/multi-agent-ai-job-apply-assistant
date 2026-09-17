"""
Flask 应用入口
工厂函数创建 Flask 实例，注册蓝图和中间件
"""
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.database import init_db


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)

    # 基础配置
    app.config.from_object(Config)

    # CORS 跨域（开发环境允许前端 5173 访问）
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

    # 注册蓝图
    from app.routes.health import bp as health_bp
    from app.routes.jobs import bp as jobs_bp
    from app.routes.resumes import bp as resumes_bp
    from app.routes.config_routes import bp as config_bp
    from app.routes.records import bp as records_bp
    from app.routes.agents import bp as agents_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(resumes_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(agents_bp)

    # 初始化数据库
    with app.app_context():
        init_db()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG,
    )
