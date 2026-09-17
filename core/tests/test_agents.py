"""
接口契约测试 — AI 投递助手 2.0

验证目标（防推倒核心）：
1. State schema 命名空间隔离（每个 Agent 只写自己的 namespace）
2. BaseAgent 抽象强制（不实现 run() 无法实例化）
3. 编排器容错（Agent 失败不中断整个流水线）
4. 加新 Agent 不破坏现有（接口契约稳定）

运行：cd <repo>/core && python -m pytest tests/ -v
     或 python tests/test_agents.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentState, BaseAgent, BaseOrchestrator, CollectorState, MatcherState
from agents.orchestrator import SequentialOrchestrator
from agents.collector import CollectorAgent, CollectorPersistAgent
from agents.matcher import MatcherAgent
from agents.skirmish import SkirmishAgent


# ---------- 1. State schema 命名空间隔离 ----------

def test_state_namespace_isolation():
    """每个 Agent 的 namespace 字段独立，互不污染"""
    state = AgentState()
    state.collector.raw_jobs = [{"job_id": "abc"}]
    state.matcher.direction_counts = {"ai": 1}

    assert state.collector.raw_jobs == [{"job_id": "abc"}]
    assert state.matcher.direction_counts == {"ai": 1}
    # 默认值互不影响
    assert state.skirmish.company_profiles == []


def test_state_defaults():
    """默认 State 可实例化，字段齐全"""
    state = AgentState()
    assert state.run_id
    assert isinstance(state.collector, CollectorState)
    assert isinstance(state.matcher, MatcherState)
    assert state.extra == {}


# ---------- 2. BaseAgent 抽象强制 ----------

def test_base_agent_is_abstract():
    """不实现 run() 的类不能实例化（强制接口）"""
    try:
        BaseAgent()
        assert False, "BaseAgent 不应能直接实例化"
    except TypeError:
        pass


class FakeAgent(BaseAgent):
    name = "fake"
    namespace = "extra"

    def run(self, state: AgentState) -> AgentState:
        state.extra["fake"] = "done"
        return state


def test_concrete_agent_works():
    """实现了 run() 的 Agent 正常实例化 + 执行"""
    agent = FakeAgent()
    state = AgentState()
    out = agent.run(state)
    assert out.extra["fake"] == "done"


# ---------- 3. 编排器容错 ----------

class BoomAgent(BaseAgent):
    name = "boom"
    namespace = "extra"

    def run(self, state: AgentState) -> AgentState:
        raise RuntimeError("故意失败")


def test_orchestrator_tolerates_failure():
    """一个 Agent 失败，后续 Agent 继续跑，错误记录到 extra"""
    ok = FakeAgent()
    boom = BoomAgent()
    orch = SequentialOrchestrator(agents=[ok, boom, ok])
    state = orch.run(AgentState())

    assert state.extra["fake"] == "done"
    assert len(state.extra["errors"]) == 1
    assert state.extra["errors"][0]["agent"] == "boom"
    assert "故意失败" in state.extra["errors"][0]["error"]


def test_orchestrator_strict_mode():
    """strict=True 时，Agent 失败立即抛出"""
    orch = SequentialOrchestrator(agents=[BoomAgent()], strict=True)
    try:
        orch.run(AgentState())
        assert False, "strict 模式应抛出异常"
    except RuntimeError:
        pass


# ---------- 4. 加新 Agent 不破坏现有 ----------

def test_add_new_agent_without_breaking():
    """模拟"以后加新 Agent"：注册一个新 Agent，现有接口契约不变"""
    class AnalyzerAgent(BaseAgent):
        name = "analyzer"
        namespace = "analyzer"

        def run(self, state: AgentState) -> AgentState:
            state.analyzer.market_report = {"jobs": len(state.collector.raw_jobs)}
            return state

    orch = SequentialOrchestrator(agents=[FakeAgent(), AnalyzerAgent()])
    state = orch.run(AgentState())
    assert state.analyzer.market_report == {"jobs": 0}
    assert state.extra["fake"] == "done"


# ---------- 5. 真实 Agent 接口检查（不触发网络） ----------

def test_real_agents_implement_contract():
    """真实 Agent 类的接口契约检查：name/namespace/run 齐全"""
    for cls in (CollectorAgent, CollectorPersistAgent, MatcherAgent, SkirmishAgent):
        assert cls.name, f"{cls.__name__} 缺 name"
        assert cls.namespace, f"{cls.__name__} 缺 namespace"
        assert hasattr(cls, "run"), f"{cls.__name__} 缺 run()"
        # namespace 必须是 AgentState 的字段
        assert hasattr(AgentState(), cls.namespace), (
            f"{cls.__name__} 的 namespace '{cls.namespace}' 不在 AgentState 里"
        )


if __name__ == "__main__":
    tests = [
        test_state_namespace_isolation,
        test_state_defaults,
        test_base_agent_is_abstract,
        test_concrete_agent_works,
        test_orchestrator_tolerates_failure,
        test_orchestrator_strict_mode,
        test_add_new_agent_without_breaking,
        test_real_agents_implement_contract,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{'通过' if failed == 0 else '失败'} ({len(tests) - failed}/{len(tests)})")
    sys.exit(1 if failed else 0)
