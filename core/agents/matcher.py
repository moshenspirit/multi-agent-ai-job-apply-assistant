"""
匹配 Agent — AI 投递助手 2.0

2.0 架构定稿 §3.3：极简匹配 = 方向标记（frontend/ai/both/none）+ 基础条件过滤（城市/黑名单）
不做复杂评分（广撒网，匹配要求不高）；沿用 1.0 的 6 维权重配置（保留，默认轻用）。

匹配规则（用户 8/24 需求："AI开发关键词混入销售岗噪声 → 匹配 Agent 过滤"）：
- 从 config 表读 search_keywords（方向 → 关键词映射）
- 对每条 job 的 title + skills + jd_text 做关键词命中统计
- 方向判定：frontend 命中数 / ai 命中数 → both（都有）/ frontend / ai / none
- 过滤：黑名单公司名 → 直接 none；非目标城市 → 直接 none
- 输出：matched_jobs（带 match_direction / match_score / match_reason）

输入：state.collector.raw_jobs（采集 Agent 产出；为空时从 DB 读 status=new 的岗位）
输出：state.matcher.matched_jobs + direction_counts + match_log
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .base import AgentState, BaseAgent, MatcherState

# 仓库根目录（core/agents/ 向上三级）
_ROOT = Path(__file__).resolve().parents[2]


def _ensure_backend_cwd(backend_dir: Path) -> None:
    """数据库路径是相对的（data/database.db 相对 backend 目录），统一切 cwd"""
    if not backend_dir.exists():
        raise RuntimeError(f"backend 目录不存在: {backend_dir}")
    os.chdir(backend_dir)


class MatcherAgent(BaseAgent):
    name = "matcher"
    namespace = "matcher"

    def __init__(self, backend_dir: str | Path = _ROOT / "web" / "backend", **kwargs):
        super().__init__(**kwargs)
        self.backend_dir = Path(backend_dir)
        sys.path.insert(0, str(self.backend_dir))

    # ---- 配置加载 ----

    def _load_config(self) -> dict:
        """读 1.0 config 表（单例 id=1）"""
        _ensure_backend_cwd(self.backend_dir)
        from app.database import SessionLocal
        from app.models.config_model import ConfigModel

        db = SessionLocal()
        try:
            c = db.query(ConfigModel).filter(ConfigModel.id == 1).first()
            if not c:
                return {"search_keywords": [], "filter_conditions": {}, "weights": {}}
            return {
                "search_keywords": json.loads(c.search_keywords) if c.search_keywords else [],
                "filter_conditions": json.loads(c.filter_conditions) if c.filter_conditions else {},
                "weights": json.loads(c.weights) if c.weights else {},
            }
        finally:
            db.close()

    # ---- 匹配核心 ----

    def _match_one(self, job: dict, rules: list[dict]) -> dict:
        """
        对单条 job 做方向匹配。
        rules = [{"direction": "frontend", "keywords": ["vue"]}, ...]
        返回 {direction, score_frontend, score_ai, reason}
        """
        text_parts = [job.get("title") or "", job.get("skills") or "", job.get("jd_text") or ""]
        # 只保留有内容的字段，避免重复匹配
        haystack = " ".join(p for p in text_parts if p).lower()

        scores = {}
        hits = {}
        for rule in rules:
            direction = rule.get("direction", "")
            if direction not in ("frontend", "ai"):
                continue
            kw_list = rule.get("keywords", [])
            n = 0
            matched = []
            for kw in kw_list:
                kw = str(kw).strip().lower()
                if not kw:
                    continue
                if kw in haystack:
                    n += 1
                    matched.append(kw)
            scores[direction] = n
            hits[direction] = matched

        sf = scores.get("frontend", 0)
        sa = scores.get("ai", 0)

        if sf > 0 and sa > 0:
            direction = "both"
        elif sf > 0:
            direction = "frontend"
        elif sa > 0:
            direction = "ai"
        else:
            direction = "none"

        reason = (
            f"frontend命中{hits.get('frontend', [])} ai命中{hits.get('ai', [])}"
            if direction != "none"
            else "无方向关键词命中"
        )
        return {"direction": direction, "score_frontend": sf, "score_ai": sa, "reason": reason}

    def _should_blacklist(self, job: dict, blacklist: list) -> str | None:
        """黑名单过滤。返回跳过原因或 None。

        城市过滤未启用（采集时已按城市限定，广撒网策略下不再二次过滤）。
        """
        company = (job.get("company_name") or job.get("boss_name") or "").strip()
        for b in blacklist:
            if b and b in company:
                return f"公司命中黑名单: {b}"
        return None

    # ---- 主流程 ----

    def run(self, state: AgentState) -> AgentState:
        ns: MatcherState = self.get_namespace(state)
        cfg = self._load_config()
        rules = cfg.get("search_keywords", [])
        fc = cfg.get("filter_conditions", {})
        blacklist = fc.get("blacklist", []) or []

        # 输入：优先内存 raw_jobs（新采集），为空则读 DB 未匹配岗位
        raw_jobs = state.collector.raw_jobs
        from_db = False
        if not raw_jobs:
            from_db = True
            _ensure_backend_cwd(self.backend_dir)
            from app.database import SessionLocal
            from app.models.job import Job

            db = SessionLocal()
            try:
                raw_jobs = [j.to_dict() for j in db.query(Job).filter(Job.match_direction.is_(None)).all()]
            finally:
                db.close()
            self.log(f"raw_jobs 为空，从 DB 读 {len(raw_jobs)} 条未匹配岗位")

        if not rules:
            self.log("⚠️ config.search_keywords 为空，全部标记为 none")
            rules = []

        matched = []
        direction_counts = {"frontend": 0, "ai": 0, "both": 0, "none": 0}
        log = []

        for job in raw_jobs:
            # 黑名单过滤
            skip_reason = self._should_blacklist(job, blacklist)
            if skip_reason:
                matched.append({**job, "match_direction": "none",
                                "match_reason": f"过滤: {skip_reason}",
                                "match_score_frontend": 0, "match_score_ai": 0})
                direction_counts["none"] += 1
                log.append({"job": job.get("title"), "result": "skip", "reason": skip_reason})
                continue

            # 方向匹配
            m = self._match_one(job, rules)
            matched.append({
                **job,
                "match_direction": m["direction"],
                "match_score_frontend": m["score_frontend"],
                "match_score_ai": m["score_ai"],
                "match_reason": m["reason"],
            })
            direction_counts[m["direction"]] += 1
            log.append({"job": job.get("title"), "result": m["direction"], "reason": m["reason"]})

        ns.matched_jobs = matched
        ns.direction_counts = direction_counts
        ns.match_log = log
        self.set_namespace(state, ns)

        self.log(f"匹配完成: {len(matched)} 条 → {direction_counts} (来源: {'DB' if from_db else '内存 raw_jobs'})")
        return state


class MatcherPersistAgent(BaseAgent):
    """匹配结果落库 — 更新 jobs 表的 match_direction / match_score_* / match_reason"""
    name = "matcher_persist"
    namespace = "matcher"

    def __init__(self, backend_dir: str | Path = _ROOT / "web" / "backend", **kwargs):
        super().__init__(**kwargs)
        self.backend_dir = Path(backend_dir)
        sys.path.insert(0, str(self.backend_dir))

    def run(self, state: AgentState) -> AgentState:
        ns: MatcherState = self.get_namespace(state)
        if not ns.matched_jobs:
            self.log("无匹配结果可落库，跳过")
            return state

        _ensure_backend_cwd(self.backend_dir)
        from app.database import SessionLocal
        from app.models.job import Job

        db = SessionLocal()
        updated = 0
        try:
            for job in ns.matched_jobs:
                source_url = job.get("source_url") or job.get("job_link") or ""
                if not source_url:
                    continue
                rec = db.query(Job).filter_by(source_url=source_url).first()
                if not rec:
                    continue
                rec.match_direction = job.get("match_direction")
                rec.match_score_frontend = job.get("match_score_frontend")
                rec.match_score_ai = job.get("match_score_ai")
                rec.match_reason = job.get("match_reason")
                updated += 1
            db.commit()
        finally:
            db.close()

        self.log(f"落库完成: 更新 {updated} 条 match_direction")
        return state
