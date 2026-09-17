"""
agents 包 — AI 投递助手 2.0 Agent 层

对外暴露：
    AgentState / BaseAgent / BaseOrchestrator   — 接口契约（base.py）
    CollectorAgent / CollectorPersistAgent       — 收集 Agent（可用）
    MatcherAgent / SkirmishAgent                 — 占位（接口就绪，实现待做）
    SequentialOrchestrator / build_default_pipeline — 编排器
    logging_setup 助手（setup_run_log / list_recent_logs / write_summary）— 写 2.0/logs/
"""
from .base import (
    AgentState,
    AnalyzerState,
    BaseAgent,
    BaseOrchestrator,
    CollectorState,
    MatcherState,
    SkirmishState,
)
from .collector import CollectorAgent, CollectorPersistAgent
from .matcher import MatcherAgent, MatcherPersistAgent
from .orchestrator import SequentialOrchestrator, build_default_pipeline
from .skirmish import SkirmishAgent, SkirmishPersistAgent

# 日志（按需 import）
from . import logging_setup

__all__ = [
    # 接口契约
    "AgentState",
    "AnalyzerState",
    "BaseAgent",
    "BaseOrchestrator",
    "CollectorState",
    "MatcherState",
    "SkirmishState",
    # 收集 Agent
    "CollectorAgent",
    "CollectorPersistAgent",
    # 占位 Agent
    "MatcherAgent",
    "MatcherPersistAgent",
    "SkirmishAgent",
    "SkirmishPersistAgent",
    # 编排
    "SequentialOrchestrator",
    "build_default_pipeline",
    # 日志
    "logging_setup",
]
