r"""
数据库迁移 — 给 jobs 表加 Skirmish 字段
幂等：列已存在则跳过；可重复运行。

用法：
    cd <repo>/web/backend
    python <repo>/core/scripts/migrate_jobs_skirmish.py

加的字段：
- company_profile  TEXT     — 公司信息包（被动形态生成）
- risk_flags       TEXT     — JSON 数组，DeepSeek 主动分析输出的风险标签
- risk_analyzed_at DATETIME  — 上次主动分析时间
"""
import os
import sys
from pathlib import Path

# 切到 backend 目录（数据库相对路径）：仓库根/web/backend
backend_dir = Path(__file__).resolve().parents[2] / "web" / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text

from app.database import engine, SessionLocal
from app.models.job import Job

NEW_COLUMNS = [
    ("company_profile", "TEXT"),
    ("risk_flags", "TEXT"),
    ("risk_analyzed_at", "DATETIME"),
]


def main():
    insp = inspect(engine)
    existing = {c["name"] for c in insp.get_columns("jobs")}
    to_add = [(name, typ) for name, typ in NEW_COLUMNS if name not in existing]

    if not to_add:
        print("✅ 所有字段已存在，无需迁移。")
        return

    print(f"需要加 {len(to_add)} 个字段: {[n for n, _ in to_add]}")
    with engine.begin() as conn:
        for name, typ in to_add:
            ddl_type = "TEXT" if "TEXT" in typ.upper() else "DATETIME"
            sql = f'ALTER TABLE jobs ADD COLUMN {name} {ddl_type}'
            print(f"  执行: {sql}")
            conn.execute(text(sql))

    # 重新确认
    insp = inspect(engine)
    print("\n迁移后 jobs 表字段:")
    for c in insp.get_columns("jobs"):
        marker = " (新增)" if c["name"] in [n for n, _ in to_add] else ""
        print(f"  {c['name']}: {c['type']}{marker}")


if __name__ == "__main__":
    main()
