"""
日志系统 — AI 投递助手 2.0

功能：
- 每次采集/匹配运行写一个独立日志文件到 core/logs/
- 文件名格式：collect-YYYY-MM-DD-HHMMSS.log（含 run_id 短码）
- 启动时自动清理超过最近 10 个的旧文件（轮转）
- BaseAgent.log() 同时输出控制台 + 写入文件
- Orchestrator 在关键节点（开始/结束/错误）也写摘要

设计原则（用户 2026-08-26 拍板）：
- "1 分钟看出跑没跑通" → 摘要 + 样本 + 异常，不写大数据
- 每项目一个目录（core/logs/、未来新版本/logs/）
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 日志根目录（相对调用文件）
LOG_DIR = Path(__file__).parent.parent / "logs"
MAX_LOG_FILES = 10  # 保留最近 N 次


def _setup_log_dir() -> Path:
    """确保 logs 目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def _rotate_old_logs(keep: int = MAX_LOG_FILES) -> int:
    """清理旧日志，保留最近 N 个。返回删除数量。

    排序键：文件名中的时间戳（YYYY-MM-DD-HHMMSS）+ 短 ID
    用文件名而非 mtime，原因是同秒创建多个 log 时 mtime 可能相等
    """
    if not LOG_DIR.exists():
        return 0
    logs = sorted(LOG_DIR.glob("collect-*.log"), key=_log_sort_key, reverse=True)
    deleted = 0
    for old in logs[keep:]:
        try:
            old.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted


def _log_sort_key(p: Path) -> tuple:
    """排序键：(时间戳元组, 文件名)。同秒的按文件名字典序排。

    文件名格式: collect-YYYY-MM-DD-HHMMSS-{short_id}.log
    short_id 可能含 '-'（如 'test-03'），所以按 'collect-' 前缀切片 + mtime 兜底
    """
    name = p.stem  # 不含扩展名
    prefix = "collect-"
    if name.startswith(prefix) and len(name) > len(prefix):
        ts_part = name[len(prefix):]
        # ts_part = "YYYY-MM-DD-HHMMSS-short_id..."，前 17 字符是时间戳
        if len(ts_part) >= 17:
            try:
                y = int(ts_part[0:4])
                mo = int(ts_part[5:7])
                d = int(ts_part[8:10])
                h = int(ts_part[11:13])
                mi = int(ts_part[13:15])
                s = int(ts_part[15:17])
                ts_key = (y, mo, d, h, mi, s)
            except (ValueError, IndexError):
                ts_key = (0, 0, 0, 0, 0, 0)
        else:
            ts_key = (0, 0, 0, 0, 0, 0)
    else:
        ts_key = (0, 0, 0, 0, 0, 0)
    # 同秒的用文件名兜底（保持稳定顺序）
    return (ts_key, name)


def setup_run_log(run_id: str = "", level: int = logging.INFO) -> tuple[logging.Logger, Path]:
    """
    初始化本次运行的文件 logger。

    返回 (logger, log_path)。后续 BaseAgent.log(msg) 会自动写入。
    进程退出时无需 close（直接以新文件覆盖即可）。
    """
    _setup_log_dir()
    _rotate_old_logs()

    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    short_id = run_id[:8] if run_id else "no-id"
    filename = f"collect-{ts}-{short_id}.log"
    log_path = LOG_DIR / filename

    # 文件 logger（独立于 root logger，避免污染其他模块）
    logger = logging.getLogger(f"collect.{ts}.{short_id}")
    logger.setLevel(level)
    logger.propagate = False  # 不传到 root

    # 清 handler（避免重复调用时堆积）
    logger.handlers.clear()

    # 文件 handler（UTF-8，保留中文）
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(fh)

    # 启动横幅
    logger.info("=" * 70)
    logger.info(f"AI 投递助手 Agent 运行日志  |  run_id={run_id}  |  log={log_path.name}")
    logger.info("=" * 70)

    return logger, log_path


def list_recent_logs(limit: int = MAX_LOG_FILES) -> list[dict]:
    """列出最近 N 次日志（用于诊断：上次跑得怎样）"""
    if not LOG_DIR.exists():
        return []
    logs = sorted(LOG_DIR.glob("collect-*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in logs[:limit]:
        stat = p.stat()
        out.append({
            "name": p.name,
            "size_kb": round(stat.st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return out


# ---- 摘要写入辅助函数 ----

def write_section(logger: logging.Logger, title: str) -> None:
    logger.info("")
    logger.info(f"--- {title} ---")


def write_summary(logger: logging.Logger, state) -> None:
    """
    写一次完整摘要（采集 + 落库 + 匹配 + 错误），用 state.extra 等
    设计成"末尾一次性写"，方便人看 log 第一眼判断成败
    """
    c = state.collector
    m = state.matcher

    write_section(logger, "采集结果")
    logger.info(f"关键词: {c.keyword or '(空)'} | 城市: {c.city or '(空)'} | 页数: {c.pages}")
    if c.stats:
        logger.info(f"抓取 total: {c.stats.get('total', 0)}")
        if c.stats.get("persisted"):
            p = c.stats["persisted"]
            logger.info(f"落库: 新增 {p.get('new', 0)} / 重复 {p.get('dup', 0)} / 跳过 {p.get('skip', 0)} / 批次 {p.get('batch', '-')}")
    if c.finished_at:
        logger.info(f"完成时间: {c.finished_at}")

    write_section(logger, "样本（前 3 条）")
    for j in c.raw_jobs[:3]:
        title = j.get("title") or j.get("job_name") or "?"
        salary = j.get("salary") or "?"
        company = j.get("boss_name") or j.get("company_name") or "?"
        location = j.get("location") or j.get("city") or ""
        logger.info(f"  • {title} | {salary} | {company} | {location}")

    write_section(logger, "匹配分布")
    if m.direction_counts:
        logger.info(f"  {m.direction_counts}")
    else:
        logger.info("  （未跑匹配）")

    errs = state.extra.get("errors") or []
    if errs:
        write_section(logger, "异常记录")
        for e in errs:
            logger.info(f"  ✗ {e.get('agent')}: {e.get('type')} - {e.get('error')[:200]}")
    else:
        write_section(logger, "异常记录")
        logger.info("  （无）")

    logger.info("=" * 70)
    logger.info("END OF RUN")
    logger.info("=" * 70)
