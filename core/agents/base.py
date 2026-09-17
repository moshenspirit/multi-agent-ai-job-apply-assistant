"""
Agent 接口契约 — AI 投递助手 2.0

设计目标（用户 2026-08-26 拍板）：
- 一开始就决定 Multi-Agent，但**不把 Agent 数量写死**
- 加新 Agent = 写一个新 class + 加一段 State 字段，**不动其他 Agent / 不动框架**
- 短期用朴素 Python class 快速出活，后期可整体替换成 LangGraph 图（接口不变）

核心约定：
1. 所有 Agent 继承 BaseAgent，实现 run(state) -> state
2. State 用 Pydantic BaseModel，字段按命名空间分区（collector.* / matcher.* / analyzer.*）
3. Agent 之间共享 State（Scratchpad 模式），不直接互相调用
4. 每个 Agent 只读自己 namespace 的输入字段 + 公共字段，只写自己 namespace 的输出字段

状态流：
    [collector.*] --raw_jobs--> [matcher.*] --matched--> [analyzer.*] / [skirmish.*]
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# 一、共享 State schema（命名空间分区）
# ============================================================

class CollectorState(BaseModel):
    """收集 Agent 的输出 — 一次采集会话的结果（对应"隔 2-3 天上班一次"）"""
    collection_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    keyword: str = ""
    city: str = ""
    pages: int = 3
    filters: Dict[str, Any] = Field(default_factory=dict)
    raw_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    stats: Dict[str, Any] = Field(default_factory=dict)  # {total, new, dup, by_keyword, scraped_at}
    finished_at: Optional[str] = None


class MatcherState(BaseModel):
    """匹配 Agent 的输出 — 方向标记 + 基础过滤（极简，广撒网）"""
    matched_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    direction_counts: Dict[str, int] = Field(default_factory=dict)  # {frontend: n, ai: n, both: n, none: n}
    match_log: List[Dict[str, Any]] = Field(default_factory=list)


class SkirmishState(BaseModel):
    """公司避坑 Agent 的输出 — 公司信息包 + 隐患提示（只做参考，用户判读）"""
    company_profiles: List[Dict[str, Any]] = Field(default_factory=list)
    risk_flags: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyzerState(BaseModel):
    """（预留）数据分析 Agent — 后续根据收集数据设计"""
    market_report: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    """全局共享 State — 所有 Agent 读写同一份，按命名空间分区"""
    # 公共元数据
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # 命名空间分区（每加一个新 Agent，在这里加一段字段）
    collector: CollectorState = Field(default_factory=CollectorState)
    matcher: MatcherState = Field(default_factory=MatcherState)
    skirmish: SkirmishState = Field(default_factory=SkirmishState)
    analyzer: AnalyzerState = Field(default_factory=AnalyzerState)

    # 任意扩展字段（给未来未知 Agent 预留，避免推倒）
    extra: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# 二、BaseAgent 抽象类
# ============================================================

class BaseAgent(ABC):
    """
    所有 Agent 的接口契约。

    子类必须实现：
        name      — Agent 标识（如 "collector"），用于日志/追踪
        namespace — 本 Agent 读写的 State 字段名（如 "collector"）
        run(state) — 输入 AgentState，处理，返回更新后的 AgentState

    约定：
    - run() 只应读取 state.<namespace> 的输入字段 + 公共字段
    - run() 只应写入 state.<namespace> 的输出字段（或 state.extra）
    - run() 内失败 → 抛异常由编排层捕获（本文件不处理业务异常）
    - 幂等：同一输入重复 run 不应产生副作用（采集除外，采集天然有网络 IO）
    """

    # 子类覆盖
    name: str = "base"
    namespace: str = "base"

    def __init__(self, **kwargs: Any):
        self.config: Dict[str, Any] = kwargs  # 每个 Agent 的专属配置（LLM key、路径等）

    @abstractmethod
    def run(self, state: AgentState) -> AgentState:
        """执行 Agent 逻辑，返回更新后的 state。"""
        raise NotImplementedError

    # ---- 公共工具（子类可复用） ----

    def log(self, msg: str, level: str = "info") -> None:
        """统一日志出口：控制台 + 文件（如果 setup_run_log 已初始化）"""
        # 控制台（始终输出，bat 用户能看到）
        print(f"[{self.name}] {msg}")
        # 文件（如果当前 AgentState 上挂了 logger）
        # 简化：直接用 _file_logger 单例
        logger = getattr(BaseAgent, "_file_logger", None)
        if logger is not None:
            log_fn = getattr(logger, level, logger.info)
            log_fn(f"[{self.name}] {msg}")

    @classmethod
    def set_file_logger(cls, logger) -> None:
        """编排器在跑流水线前调用，把文件 logger 挂到所有 Agent"""
        cls._file_logger = logger

    @classmethod
    def clear_file_logger(cls) -> None:
        cls._file_logger = None

    def get_namespace(self, state: AgentState) -> BaseModel:
        """取本 Agent 的命名空间（类型安全访问）"""
        return getattr(state, self.namespace)

    def set_namespace(self, state: AgentState, value: BaseModel) -> AgentState:
        """写回本 Agent 的命名空间"""
        setattr(state, self.namespace, value)
        return state

    def validate(self, state: AgentState) -> None:
        """（可选覆盖）run 前校验输入完整性，抛 ValueError 拒绝执行"""
        pass


# ============================================================
# 三、编排层最小契约（后期换 LangGraph 时，这个接口保持不变）
# ============================================================

class BaseOrchestrator(ABC):
    """
    编排器抽象 — 决定 Agent 以什么顺序/拓扑跑。

    2.0 短期：SequentialOrchestrator（线性串，最朴素）
    后期：   LangGraph StateGraph 实现（接口不变，内部换图）
    """

    @abstractmethod
    def run(self, initial_state: AgentState) -> AgentState:
        """按编排规则跑完所有 Agent，返回最终 state。"""
        raise NotImplementedError
