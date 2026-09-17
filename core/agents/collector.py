"""
收集 Agent — AI 投递助手 2.0 第一版

职责：隔 2-3 天"上一次班"，跑 boss-zhipin-scraper 抓取 BOSS 岗位，结果写入共享 State。

实现说明（快速出活，不追求完美）：
- 直接 import `boss_cdp_raw.py` 的 `scrape_list()`（纯 Python API，非 subprocess）
- scrape_list 内部已包含：resolve_city / CDP 连接 / 被动捕获 / 翻页随机延迟 / code 37 识别
- 本 Agent 只负责：编排参数、调用、把结果塞进 state.collector
- **不落库**：落库交给 CollectorPersistAgent（或由编排层在收集后统一落库）
  这样收集 Agent 保持"纯采集"职责，数据库 schema 变化不影响它
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from .base import AgentState, BaseAgent, CollectorState

# 仓库根目录（core/agents/ 向上三级）
_ROOT = Path(__file__).resolve().parents[2]

# boss-zhipin-scraper 默认位置（仓库根 tools/ 下，第三方工具，见 README；可被 config 覆盖）
SCRAPER_DIR = _ROOT / "tools" / "boss-zhipin-scraper" / "scripts"


class CollectorAgent(BaseAgent):
    name = "collector"
    namespace = "collector"

    def __init__(self, scraper_dir: str | Path = SCRAPER_DIR, **kwargs):
        super().__init__(**kwargs)
        self.scraper_dir = Path(scraper_dir)
        sys.path.insert(0, str(self.scraper_dir))

    def run(self, state: AgentState) -> AgentState:
        ns: CollectorState = self.get_namespace(state)

        # 1. 参数校验
        if not ns.keyword:
            raise ValueError("CollectorAgent: keyword 为空，无法采集")
        if not ns.city:
            raise ValueError("CollectorAgent: city 为空，无法采集")

        # 2. 调用 scraper（延迟 import：只有真正跑采集才加载 CDP 依赖）
        try:
            from boss_cdp_raw import scrape_list
        except ImportError as e:
            raise RuntimeError(
                f"CollectorAgent: 无法导入 boss_cdp_raw（{e}）。"
                f"请确认 scraper 目录存在：{self.scraper_dir}"
            ) from e

        self.log(f"开始采集: keyword={ns.keyword} city={ns.city} pages={ns.pages}")

        # scrape_list 签名（v2.2.0）：
        #   scrape_list(keyword, city_input, max_pages, filters, output_path,
        #               cdp_port=9222, fmt="json", allow_dom_fallback=False)
        # 返回: {"keyword", "city", "total", "jobs": [...]}
        # 注意: output_path=None 时 scrape_list 会写默认路径
        #   (~/.boss-zhipin-scraper/job-result/boss_jobs_*.json)，可接受；
        #   真实落库以内存 raw_jobs 为准（CollectorPersistAgent）。
        result = scrape_list(
            keyword=ns.keyword,
            city_input=ns.city,
            max_pages=ns.pages,
            filters=ns.filters,
            output_path=None,   # 让 scrape_list 写默认路径（无副作用）
            cdp_port=self.config.get("cdp_port", 9222),
        )

        jobs = result.get("jobs", [])
        ns.raw_jobs = jobs
        ns.stats = {
            "total": result.get("total", len(jobs)),
            "by_keyword": {ns.keyword: len(jobs)},
            "scraped_at": datetime.now().isoformat(),
            "scraper_version": "v2.2.0",
        }
        ns.finished_at = datetime.now().isoformat()

        self.log(f"采集完成: {len(jobs)} 条 (keyword={ns.keyword})")
        self.set_namespace(state, ns)
        return state


class CollectorPersistAgent(BaseAgent):
    """
    收集落库 Agent — 把 state.collector.raw_jobs 写入 jobs 表。

    与 CollectorAgent 分离的原因：
    - 采集（网络 IO，可能失败）与落库（本地 IO，稳定）解耦
    - 落库逻辑可复用 web 的 import_boss_json.py 解析规则
    - 以后收集 Agent 换 LangGraph 实现时，落库逻辑不用动
    """
    name = "collector_persist"
    namespace = "collector"

    def run(self, state: AgentState) -> AgentState:
        ns: CollectorState = self.get_namespace(state)
        if not ns.raw_jobs:
            self.log("无数据可落库，跳过")
            return state

        # 复用 web 的导入逻辑（parse_salary / parse_tags / parse_district）
        import sys as _sys
        import os as _os
        backend_dir = Path(self.config.get("backend_dir", _ROOT / "web" / "backend"))
        if not backend_dir.exists():
            raise RuntimeError(f"backend 目录不存在: {backend_dir}")
        _os.chdir(backend_dir)  # 数据库路径相对 backend 目录
        _sys.path.insert(0, str(backend_dir))

        from app.database import SessionLocal
        from app.models.job import Job

        from scripts.import_boss_json import parse_district, parse_salary, parse_tags

        db = SessionLocal()
        batch = datetime.now().strftime("%Y%m%d%H%M%S")
        new_cnt = dup_cnt = skip_cnt = 0

        for j in ns.raw_jobs:
            source_url = (j.get("job_link") or j.get("link") or "").strip()
            if not source_url:
                skip_cnt += 1
                continue

            if db.query(Job).filter_by(source_url=source_url).first():
                dup_cnt += 1
                continue

            tags_text = j.get("tags") or j.get("job_labels") or ""
            exp, edu = parse_tags(tags_text)
            sal_min, sal_max = parse_salary(j.get("salary") or "")
            job = Job(
                job_name=j.get("title") or "",
                company_name=j.get("boss_name") or j.get("company") or "未知",
                salary_min=sal_min,
                salary_max=sal_max,
                city=ns.city,
                district=parse_district(j.get("location") or ""),
                experience=exp,
                education=edu,
                jd_text=None,  # 详情由详情 Agent 补（本期不做）
                company_size=j.get("company_scale") or "",
                company_industry=j.get("company_industry") or "",
                company_finance=j.get("company_stage") or "",
                boss_active=j.get("boss_active_status") or "",
                source_url=source_url,
                source_keyword=ns.keyword,
                status="new",
                collect_batch=batch,
            )
            db.add(job)
            new_cnt += 1

        db.commit()
        db.close()

        ns.stats["persisted"] = {"new": new_cnt, "dup": dup_cnt, "skip": skip_cnt, "batch": batch}
        self.set_namespace(state, ns)
        self.log(f"落库完成: 新增 {new_cnt} / 重复 {dup_cnt} / 跳过 {skip_cnt} / 批次 {batch}")
        return state
