"""
公司避坑 Agent — AI 投递助手 2.0

2.0 架构定稿 §3.4（★差异化核心，双形态）：
- 被动：生成"公司+岗位信息包"文本（无 LLM 依赖），用户复制贴给 DeepSeek/ChatGPT 问坑
- 主动：可选。系统内调 LLM（LLMClient 抽象）生成风险标签
  只做参考，不下"别去"结论，用户判读为准。

设计原则（用户 2026-08-26 拍板）：
- LLM key 缺失 → 优雅降级到纯被动（不报错）
- 主动分析带 rate-limit（小公司名字易触发 LLM，频率太高耗钱）
- 输入：state.matcher.matched_jobs（或 state.collector.raw_jobs）→ 输出：state.skirmish.company_profiles + risk_flags
- 落库：SkirmishPersistAgent 写回 jobs 表的 company_profile / risk_flags / risk_analyzed_at 字段
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .base import AgentState, BaseAgent, SkirmishState

# 仓库根目录（core/agents/ 向上三级）
_ROOT = Path(__file__).resolve().parents[2]


def _ensure_backend_cwd(backend_dir: Path) -> None:
    if not backend_dir.exists():
        raise RuntimeError(f"backend 目录不存在: {backend_dir}")
    os.chdir(backend_dir)
    sys.path.insert(0, str(backend_dir))


# ===== 被动形态：纯本地生成（无 LLM 依赖）=====

def _format_company_profile(job: dict) -> str:
    """
    生成"公司+岗位信息包"文本（被动形态的产物）。
    用途：用户复制贴给 DeepSeek/ChatGPT/Claude 问"这家公司有什么坑"

    字段兼容：DB 回退用 company_name/job_name；collector 内存 raw_jobs 用 boss_name/title。
    """
    company = job.get("company_name") or job.get("boss_name") or job.get("company") or "未知"
    title = job.get("job_name") or job.get("title") or "未知"
    parts = []
    parts.append(f"【公司】{company}")
    if job.get("company_size"):
        parts.append(f"【规模】{job['company_size']}")
    if job.get("company_industry"):
        parts.append(f"【行业】{job['company_industry']}")
    if job.get("company_finance"):
        parts.append(f"【融资】{job['company_finance']}")
    parts.append("")
    parts.append(f"【岗位】{title}")
    if job.get("salary_min") or job.get("salary_max"):
        sal = []
        if job.get("salary_min"):
            sal.append(str(job["salary_min"]))
        if job.get("salary_max"):
            sal.append(str(job["salary_max"]))
        parts.append(f"【薪资】{'-'.join(sal)} 元/月")
    elif job.get("salary"):
        parts.append(f"【薪资】{job['salary']}")
    if job.get("experience"):
        parts.append(f"【经验】{job['experience']}")
    if job.get("education"):
        parts.append(f"【学历】{job['education']}")
    if job.get("city") or job.get("district"):
        loc = job.get("city") or ""
        if job.get("district"):
            loc += f" · {job['district']}"
        parts.append(f"【地点】{loc}")
    if job.get("boss_active"):
        parts.append(f"【BOSS 活跃】{job['boss_active']}")
    parts.append("")
    if job.get("jd_text"):
        parts.append(f"【JD 摘要】\n{job['jd_text'][:800]}{'...' if len(job['jd_text']) > 800 else ''}")
    return "\n".join(parts)


# ===== 主动形态：调 LLM（用户决定要不要）=====

def _analyze_risk_with_llm(llm, job: dict) -> list[dict] | None:
    """
    调 LLM 主动分析单个岗位的风险标签。

    返回值：
    - list（可能为空 []）：成功。"[]" 表示 LLM 判定"无明显风险"
    - None：调用失败（网络/解析/格式错），调用方应跳过落库

    没 LLM key 时由 SkirmishAgent 优雅跳过（这里不抛异常）。
    """
    profile = _format_company_profile(job)
    prompt = f"""分析下面这个招聘岗位的公司和岗位信息，**只做参考，不下"别去"结论**。
返回 JSON 数组（即使没有风险也返回 []），每个元素:
{{"flag": "<短标签, 英文snake_case>", "severity": "low|mid|high", "reason": "<一句话解释, 中文>"}}

重点关注：
- 公司规模与薪资倒挂（如 0-20 人公司开 30-60K）
- 行业与岗位错位（如"AI 开发"但 JD 全是销售话术）
- 招聘者 BOSS 状态异常（离线很久、突然活跃）
- 行业本身的常见坑（教培/贷超/转介绍等）
- 学历/经验要求与薪资严重不匹配

{profile}

只返回 JSON 数组，不要其他文字。"""
    try:
        result = llm.chat_json([
            {"role": "system", "content": "你是求职风险分析助手，只返回 JSON 数组。"},
            {"role": "user", "content": prompt},
        ], temperature=0.2)
        if isinstance(result, dict):
            flags = result.get("flags") or result.get("risks") or []
        else:
            flags = result
        # 校验结构
        out = []
        for f in flags:
            if isinstance(f, dict) and "flag" in f and "severity" in f and "reason" in f:
                out.append(f)
        return out
    except Exception as e:
        # 失败返回 None（区别于"成功但无风险"的 []）
        return None


# ===== Agent 类 =====

class SkirmishAgent(BaseAgent):
    name = "skirmish"
    namespace = "skirmish"

    def __init__(self, backend_dir: str | Path = _ROOT / "web" / "backend",
                 enable_active: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.backend_dir = Path(backend_dir)
        self.enable_active = enable_active
        self.llm = None
        self.llm_available = False
        if enable_active:
            try:
                from .llm_client import LLMClient
                self.llm = LLMClient.from_env()
                self.llm_available = True
            except Exception as e:
                # LLM key 缺失 → 优雅降级到纯被动
                self.llm = None
                self.llm_available = False
                # 注意：不在 __init__ 阶段打 log，留到 run() 阶段统一提示

    def run(self, state: AgentState) -> AgentState:
        ns: SkirmishState = self.get_namespace(state)
        jobs = state.matcher.matched_jobs or state.collector.raw_jobs or []
        from_db = False

        # 输入回退：和 MatcherAgent 一样，从 DB 直接读
        if not jobs:
            from_db = True
            _ensure_backend_cwd(self.backend_dir)
            from app.database import SessionLocal
            from app.models.job import Job
            db = SessionLocal()
            try:
                # 读所有未被 none 标过的（避免给"明显不匹配"的岗位生成信息包浪费 LLM 钱）
                rows = db.query(Job).filter(Job.match_direction.in_(["frontend", "ai", "both"])).all()
                jobs = [j.to_dict() for j in rows]
            finally:
                db.close()
            self.log(f"上游无输入，从 DB 读 {len(jobs)} 条（match_direction in frontend/ai/both）")

        # 过滤：跳过已经做过主动分析的（risk_flags 非 NULL）
        # 注：来自 collector 的 raw_jobs（内存）走完整分析；来自 DB 回退走增量分析
        if from_db and self.llm_available:
            before = len(jobs)
            jobs = [j for j in jobs if j.get("risk_flags") is None]
            skipped = before - len(jobs)
            if skipped:
                self.log(f"跳过 {skipped} 条已分析过的岗位（risk_flags 非空）")

        if not jobs:
            self.log("无可分析岗位，跳过")
            return state

        # 提示 LLM 状态
        if self.enable_active and not self.llm_available:
            self.log("LLM key 未配置，仅生成被动形态（公司信息包）")
        elif self.enable_active and self.llm:
            self.log(f"LLM 已就绪（provider={self.llm.provider}），被动 + 主动双形态")

        profiles = []
        risks = []
        active_count = 0

        for job in jobs:
            # 被动：必跑
            profile_text = _format_company_profile(job)
            profiles.append({
                "job_id": job.get("source_url") or job.get("job_link") or "",
                "job_name": job.get("job_name") or job.get("title") or "",
                "company_name": job.get("company_name") or job.get("boss_name") or "",
                "profile_text": profile_text,
            })

            # 主动：可选（每个 job 调一次 LLM）
            if self.llm_available and self.llm:
                risk_flags = _analyze_risk_with_llm(self.llm, job)
                # 语义：list（包含 []）= 成功；None = 失败
                if risk_flags is not None:
                    # [] 也存 —— 标记"已分析过、无明显风险"，下次跳过 LLM
                    risks.append({
                        "job_id": profiles[-1]["job_id"],
                        "job_name": profiles[-1]["job_name"],
                        "company_name": profiles[-1]["company_name"],
                        "flags": risk_flags,
                        "analyzed_at": datetime.now().isoformat(),
                    })
                    active_count += 1
                else:
                    self.log(f"  ⚠️ LLM 分析失败: {profiles[-1]['job_name']} | {profiles[-1]['company_name']}")

        ns.company_profiles = profiles
        ns.risk_flags = risks
        self.set_namespace(state, ns)

        self.log(f"完成: 被动信息包 {len(profiles)} 条, 主动风险分析 {active_count}/{len(jobs)} 条")
        return state


class SkirmishPersistAgent(BaseAgent):
    """避坑结果落库 — 写回 jobs 表的 company_profile / risk_flags / risk_analyzed_at"""
    name = "skirmish_persist"
    namespace = "skirmish"

    def __init__(self, backend_dir: str | Path = _ROOT / "web" / "backend", **kwargs):
        super().__init__(**kwargs)
        self.backend_dir = Path(backend_dir)

    def run(self, state: AgentState) -> AgentState:
        ns: SkirmishState = self.get_namespace(state)
        if not ns.company_profiles and not ns.risk_flags:
            self.log("无避坑结果可落库，跳过")
            return state

        _ensure_backend_cwd(self.backend_dir)
        from app.database import SessionLocal
        from app.models.job import Job

        # 构造 source_url → profile/risk 的映射
        profile_map = {p["job_id"]: p["profile_text"] for p in ns.company_profiles}
        risk_map = {r["job_id"]: r for r in ns.risk_flags}

        db = SessionLocal()
        updated = 0
        try:
            for job_id, profile_text in profile_map.items():
                if not job_id:
                    continue
                rec = db.query(Job).filter_by(source_url=job_id).first()
                if not rec:
                    continue
                rec.company_profile = profile_text
                if job_id in risk_map:
                    r = risk_map[job_id]
                    rec.risk_flags = json.dumps(r["flags"], ensure_ascii=False)
                    rec.risk_analyzed_at = datetime.fromisoformat(r["analyzed_at"])
                updated += 1
            db.commit()
        finally:
            db.close()

        self.log(f"落库完成: 更新 {updated} 条 (company_profile / risk_flags)")
        return state
