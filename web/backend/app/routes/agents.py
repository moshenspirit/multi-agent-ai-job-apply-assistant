"""
Agent 管理 API 路由 — 采集 / 匹配 / 避坑 Agent 的配置、触发、状态

设计：Agent 注册表（AGENTS dict）驱动。
加新 Agent = 注册表加一条（label/description/fields/script/extra_args），
前端表单由 fields 自动渲染，不用改页面结构。
"""
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

from app.database import SessionLocal
from app.models.agent_config import AgentConfig

bp = Blueprint("agents", __name__, url_prefix="/api/agents")

# ===== 常量 =====
# 运行 core 脚本的解释器：默认复用当前后端解释器（web + core 依赖装在同一环境即可），
# 也可用 AGENT_PYTHON 环境变量指向其它虚拟环境
BASE_PYTHON = os.getenv("AGENT_PYTHON", sys.executable)
BASE_DIR = Path(__file__).resolve().parents[4] / "core"   # run_*.py 所在目录（仓库根/core）
LOGS_DIR = BASE_DIR / "logs"                      # 2.0 日志（collect-*.log）

# ===== Agent 注册表（可延展：加 Agent = 这里加一条）=====
AGENTS = {
    "collector": {
        "label": "采集 Agent",
        "description": "BOSS 直聘岗位采集（半自动）。前置条件：手机数据热点 + 专用 Chrome 已启动（先跑 启动Chrome.bat）",
        "fields": [
            {"key": "keyword", "label": "关键词", "type": "text", "default": "AI开发"},
            {"key": "city", "label": "城市", "type": "text", "default": "广州"},
            {"key": "pages", "label": "抓取页数", "type": "number", "default": 1, "min": 1, "max": 10},
        ],
        "script": "scripts/run_collector.py",
        # 注意：run_collector.py 默认即全链路（采集→落库→匹配→落库→避坑→落库），
        # 与「采集一次.bat」行为一致。无 --persist 参数（只有 --no-persist），
        # 曾误传 ["--persist"] 导致 argparse exit 2 —— 2026-09-03 修复
        "extra_args": [],
    },
    "matcher": {
        "label": "匹配 Agent",
        "description": "方向标记（frontend / ai / both / none）+ 过滤。方向关键词在「配置中心」页面管理",
        "fields": [],
        "script": "scripts/run_matcher.py",
        "extra_args": ["--persist"],
    },
    "skirmish": {
        "label": "避坑 Agent",
        "description": "公司信息包（被动）+ 风险分析（主动，需 DeepSeek key）。分析结果仅供参考，以你的判断为准",
        "fields": [
            {"key": "enable_active", "label": "主动风险分析（DeepSeek）", "type": "boolean", "default": True},
        ],
        "script": "scripts/run_skirmish.py",
        "extra_args": ["--persist"],
    },
}

# 运行状态（内存。Flask 重启后清空，last_run 从日志目录补）
RUN_STATE: dict[str, dict] = {}
_LOCK = threading.Lock()


# ===== 工具 =====

def _db_configs() -> dict[str, dict]:
    """读全部 Agent 配置 → {name: config_dict}"""
    db = SessionLocal()
    try:
        return {c.name: json.loads(c.config_json or "{}") for c in db.query(AgentConfig).all()}
    finally:
        db.close()


def _merged_config(name: str, db_cfg: dict) -> dict:
    """DB 配置 + 注册表默认值合并（缺字段用默认）"""
    meta = AGENTS[name]
    merged = {}
    for f in meta["fields"]:
        merged[f["key"]] = db_cfg.get(f["key"], f["default"])
    return merged


def _build_args(name: str, config: dict) -> list[str]:
    """配置 → run_*.py 命令行参数"""
    if name == "collector":
        kw = config.get("keyword") or "AI开发"
        city = config.get("city") or "广州"
        pages = int(config.get("pages") or 1)
        pages = max(1, min(pages, 10))
        return ["--keyword", kw, "--city", city, "--pages", str(pages)]
    if name == "skirmish":
        return ["--no-active"] if not config.get("enable_active", True) else []
    return []


def _read_latest_log(max_chars: int = 3000, prefer_path: str | None = None) -> dict | None:
    """读日志尾部。

    prefer_path：优先读指定日志文件（= 该 Agent 上次运行的日志文件名，
    2026-09-03 修复：此前 3 个 Agent 卡片都显示同一个全局最新 collect-*.log）。
    注意 RUN_STATE 在 Flask 重启后清空，log_path 丢失时回落读全局最新日志。
    """
    if prefer_path:
        p = LOGS_DIR / prefer_path
        if p.exists():
            return _read_log_tail(p, max_chars)

    # 回落：读 logs 最新 collect-*.log
    if not LOGS_DIR.exists():
        return None
    logs = sorted(LOGS_DIR.glob("collect-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return None
    return _read_log_tail(logs[0], max_chars)


def _read_log_tail(p: Path, max_chars: int) -> dict | None:
    """读单个日志文件的尾部信息"""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return {
        "path": p.name,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
        "tail": text[-max_chars:],
    }


def _agent_status(name: str) -> dict:
    with _LOCK:
        st = dict(RUN_STATE.get(name, {}))
    running = bool(st.get("running"))
    # 优先该 Agent 上次运行的日志文件（log_path 在 run 完成线程里记录）
    log = _read_latest_log(prefer_path=st.get("log_path"))
    last_run = None
    if st.get("finished_at"):
        last_run = {
            "started_at": st.get("started_at"),
            "finished_at": st.get("finished_at"),
            "exit_code": st.get("exit_code"),
            "log_path": st.get("log_path"),
        }
    return {"running": running, "last_run": last_run, "log": log}


# ===== 路由 =====

@bp.route("", methods=["GET"])
def list_agents():
    """Agent 列表：注册表信息 + 配置 + 运行状态"""
    db_cfg = _db_configs()
    out = []
    for name, meta in AGENTS.items():
        merged = _merged_config(name, db_cfg.get(name, {}))
        status = _agent_status(name)
        out.append({
            "name": name,
            "label": meta["label"],
            "description": meta["description"],
            "fields": meta["fields"],
            "config": merged,
            "running": status["running"],
            "last_run": status["last_run"],
            "log": status["log"],
        })
    return jsonify({"agents": out})


@bp.route("/<name>/config", methods=["PUT"])
def save_config(name: str):
    """保存 Agent 配置（只存注册表 fields 里声明的字段）"""
    if name not in AGENTS:
        return jsonify({"error": f"未知 Agent: {name}"}), 404
    data = request.get_json() or {}
    config = data.get("config") or {}
    valid_keys = {f["key"] for f in AGENTS[name]["fields"]}
    clean = {k: v for k, v in config.items() if k in valid_keys}

    db = SessionLocal()
    try:
        rec = db.query(AgentConfig).filter(AgentConfig.name == name).first()
        if rec:
            rec.config_json = json.dumps(clean, ensure_ascii=False)
        else:
            rec = AgentConfig(name=name, config_json=json.dumps(clean, ensure_ascii=False))
            db.add(rec)
        db.commit()
        db.refresh(rec)
        return jsonify({"ok": True, **rec.to_dict()})
    finally:
        db.close()


@bp.route("/<name>/run", methods=["POST"])
def run_agent(name: str):
    """后台线程触发 Agent 运行（采集可能 30-60 分钟，不能阻塞 HTTP）"""
    if name not in AGENTS:
        return jsonify({"error": f"未知 Agent: {name}"}), 404

    with _LOCK:
        st = RUN_STATE.setdefault(name, {})
        if st.get("running"):
            return jsonify({"error": f"{AGENTS[name]['label']} 正在运行中"}), 409

        db_cfg = _db_configs().get(name, {})
        config = _merged_config(name, db_cfg)
        args = _build_args(name, config)
        meta = AGENTS[name]

        script = str(BASE_DIR / meta["script"])
        cmd = [BASE_PYTHON, script, *meta["extra_args"], *args]
        st.update({
            "running": True,
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "exit_code": None,
            "cmd": " ".join(cmd),
        })
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _wait():
        code = proc.wait()
        with _LOCK:
            st = RUN_STATE.get(name, {})
            st["running"] = False
            st["exit_code"] = code
            st["finished_at"] = datetime.now().isoformat(timespec="seconds")
            latest = _read_latest_log()
            st["log_path"] = latest["path"] if latest else None

    threading.Thread(target=_wait, daemon=True).start()

    return jsonify({"ok": True, "name": name, "started_at": st["started_at"]})


@bp.route("/<name>/status", methods=["GET"])
def get_status(name: str):
    """Agent 运行状态 + 最近日志"""
    if name not in AGENTS:
        return jsonify({"error": f"未知 Agent: {name}"}), 404
    return jsonify(_agent_status(name))
