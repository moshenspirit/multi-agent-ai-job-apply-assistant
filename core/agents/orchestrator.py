"""
编排器 — 短期朴素实现，后期整体换成 LangGraph

设计（用户 2026-08-26 拍板）：
- 2.0 短期：SequentialOrchestrator（线性串，最快出活）
- 后期：LangGraph StateGraph 实现（接口不变，内部换图）
- 接口契约 = BaseOrchestrator.run(initial_state) -> final_state

加新 Agent 的流程（防推倒核心）：
1. 在 base.py 的 AgentState 加一段命名空间字段（如 analyzer: AnalyzerState）
2. 写一个新 class 继承 BaseAgent（name/namespace/run）
3. 在 orchestrator 的 agent 列表里加一行
4. 跑 tests/test_agents.py 验证接口契约没被破坏
"""
from __future__ import annotations

from .base import AgentState, BaseAgent, BaseOrchestrator


class SequentialOrchestrator(BaseOrchestrator):
    """
    线性编排：按注册顺序依次跑每个 Agent，每个 Agent 更新共享 State。
    一个 Agent 失败 → 记录错误到 state.extra，继续跑后续（默认）或停止（strict=True）。

    日志（2026-08-26 加）：
    - run() 开头自动初始化文件 logger（2.0/logs/collect-*.log）+ 10 个轮转
    - 所有 Agent 的 self.log() 同时输出控制台 + 写文件
    - run() 结尾自动写一份完整摘要（采集/落库/匹配/异常）
    """

    def __init__(self, agents: list[BaseAgent], strict: bool = False, enable_file_log: bool = True):
        self.agents = agents
        self.strict = strict
        self.enable_file_log = enable_file_log

    def run(self, initial_state: AgentState) -> AgentState:
        state = initial_state
        errors = []

        # 初始化文件 logger
        logger = None
        if self.enable_file_log:
            from .logging_setup import setup_run_log, write_summary
            logger, log_path = setup_run_log(run_id=state.run_id)
            BaseAgent.set_file_logger(logger)
            print(f"[orchestrator] 📄 日志已写入: {log_path}")

        try:
            for agent in self.agents:
                try:
                    agent.validate(state)
                    state = agent.run(state)
                except Exception as e:  # noqa: BLE001 — 编排层捕获所有 Agent 异常
                    errors.append({"agent": agent.name, "error": str(e), "type": type(e).__name__})
                    state.extra["errors"] = errors
                    if self.strict:
                        raise
                    msg = f"⚠️ Agent '{agent.name}' 失败（已跳过，继续后续）: {e}"
                    print(f"[orchestrator] {msg}")
                    if logger:
                        logger.warning(msg)

            state.extra["errors"] = errors

            # 写摘要（末尾一次性）
            if logger:
                from .logging_setup import write_summary
                write_summary(logger, state)
        finally:
            if self.enable_file_log:
                BaseAgent.clear_file_logger()

        return state


def build_default_pipeline(collector_kwargs: dict | None = None) -> SequentialOrchestrator:
    """
    默认流水线：采集 → 落库 → 匹配 → 落库 → 避坑 → 落库
    （采集 Agent 网络 IO 可能失败；匹配/避坑为本地 + LLM，失败会记录到 state.extra 并继续）

    collector_kwargs: 传给 CollectorAgent 的配置（scraper_dir / cdp_port 等）
    """
    from .collector import CollectorAgent, CollectorPersistAgent
    from .matcher import MatcherAgent, MatcherPersistAgent
    from .skirmish import SkirmishAgent, SkirmishPersistAgent

    ck = collector_kwargs or {}

    return SequentialOrchestrator(
        agents=[
            CollectorAgent(**ck),
            CollectorPersistAgent(),
            MatcherAgent(),
            MatcherPersistAgent(),
            SkirmishAgent(),
            SkirmishPersistAgent(),
        ],
        strict=False,
    )
