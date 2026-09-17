# AI 投递助手 2.0 — Agent 架构设计（接口契约）

> **代号：2026H2P | 日期：2026-08-26**
> 状态：**接口契约已定稿，实现分阶段**（收集 Agent 可用，匹配/避坑占位）
> 上游输入：《架构定稿.md》（§3.5 自研编排）+《采集运行模式深度调研.md》（方案 C = 隔 2-3 天批量）

---

## 〇、设计目标（用户 2026-08-26 拍板）

1. **一开始就决定 Multi-Agent**，但不把 Agent 数量写死
2. **加新 Agent = 写一个新 class + 加一段 State 字段**，不动其他 Agent / 不动框架
3. 短期朴素 Python class **快速出活**，后期可整体替换成 **LangGraph 图**（接口不变）
4. 用户原话："避免后面有什么需要，把整个项目推翻重写，注重可拓展性和开发上限、开发灵活度"

**核心原则：接口先、实现后换。** 接口契约（本文件）= 防推倒的地基；LangGraph = 后期可替换的表达方式。

---

## 一、接口契约（三层）

```
┌─ ① State schema（数据契约）────────────────────────────┐
│  AgentState (Pydantic BaseModel)                        │
│  ├── run_id / started_at          ← 公共元数据           │
│  ├── collector: CollectorState     ← 收集 Agent 命名空间  │
│  ├── matcher: MatcherState         ← 匹配 Agent 命名空间  │
│  ├── skirmish: SkirmishState       ← 避坑 Agent 命名空间  │
│  ├── analyzer: AnalyzerState       ← 预留（数据分析）     │
│  └── extra: dict                   ← 任意扩展（未知 Agent）│
└────────────────────────────────────────────────────────┘
┌─ ② BaseAgent（行为契约）───────────────────────────────┐
│  name: str          — Agent 标识（日志/追踪）            │
│  namespace: str     — 读写 State 的字段名               │
│  run(state) -> state — 输入 AgentState，输出更新后 State │
│  约定：只读自己 namespace + 公共字段；只写自己 namespace  │
└────────────────────────────────────────────────────────┘
┌─ ③ BaseOrchestrator（编排契约）─────────────────────────┐
│  run(initial_state) -> final_state                     │
│  短期：SequentialOrchestrator（线性串）                  │
│  后期：LangGraph StateGraph（接口不变）                  │
└────────────────────────────────────────────────────────┘
```

**文件位置**（本仓库 `core/` 目录）：

| 文件 | 内容 | 状态 |
|---|---|---|
| `agents/base.py` | State schema + BaseAgent + BaseOrchestrator | ✅ 定稿 |
| `agents/collector.py` | CollectorAgent + CollectorPersistAgent | ✅ 可用（调 scrape_list） |
| `agents/matcher.py` | MatcherAgent + MatcherPersistAgent | ⬜ 占位 |
| `agents/skirmish.py` | SkirmishAgent + SkirmishPersistAgent | ⬜ 占位 |
| `agents/orchestrator.py` | SequentialOrchestrator + build_default_pipeline | ✅ 可用 |
| `tests/test_agents.py` | 接口契约测试（8 个用例） | ✅ 8/8 通过 |
| `graphs/` | （预留）LangGraph 图 | ⬜ 空 |

---

## 二、State schema 命名空间规则（防互踩）

每个 Agent 的输入/输出**只在它自己的命名空间字段里**：

| namespace | 谁写 | 谁读 | 内容 |
|---|---|---|---|
| `collector` | CollectorAgent | matcher/skirmish | raw_jobs / stats / finished_at |
| `matcher` | MatcherAgent | skirmish/展示层 | matched_jobs / direction_counts |
| `skirmish` | SkirmishAgent | 展示层 | company_profiles / risk_flags |
| `analyzer` | （预留） | 展示层 | market_report |
| `extra` | 任意 | 任意 | 临时/未知扩展 |

**为什么用 Pydantic 而不是 dict**：强校验——Agent A 写错类型（如 raw_jobs 传了字符串），跑起来立刻报错，而不是静默污染下游。

---

## 三、加一个新 Agent 的 5 步流程（防推倒核心）

假设以后要加"数据分析 Agent"（analyzer）：

```python
# 第 1 步：base.py 的 AgentState 加一段命名空间（如果还没有）
analyzer: AnalyzerState = Field(default_factory=AnalyzerState)

# 第 2 步：写一个新类，继承 BaseAgent
class AnalyzerAgent(BaseAgent):
    name = "analyzer"
    namespace = "analyzer"
    def run(self, state: AgentState) -> AgentState:
        # 读上游：state.collector.raw_jobs / state.matcher.matched_jobs
        # 写自己：state.analyzer.market_report = {...}
        return state

# 第 3 步：orchestrator.py 的 build_default_pipeline 加一行
SequentialOrchestrator(agents=[..., AnalyzerAgent()])

# 第 4 步：跑测试，验证接口契约没被破坏
python tests/test_agents.py   # 应 8/8 或 9/9 通过

# 第 5 步：如果新 Agent 有持久化需求，再加一个 XxxPersistAgent
```

**全程不动**：其他 Agent 的代码、编排器逻辑、State 已有字段。这就是"防推倒"。

---

## 四、LangGraph 迁移路径（后期，接口不变）

| 现在（短期朴素） | 后期（LangGraph） | 变化 |
|---|---|---|
| `SequentialOrchestrator` | `StateGraph` + node 注册 | 编排器内部换，接口 `run(state)` 不变 |
| 每个 Agent 一个 class | 每个 Agent 一个 node 函数 | node 函数内部调 Agent.run() 或直接写逻辑 |
| 线性拓扑 | 可加 Conditional Edge / Supervisor | 图结构自由 |
| 无持久化 | SqliteSaver checkpoint | 增量 |
| 无追踪 | LangSmith tracing | 增量 |

**为什么用 LangGraph 而不是 CrewAI**（用户 2026-08-26 拍板 + AI 推断标注）：
- CrewAI 把角色绑死（Sequential/Hierarchical Crew），加角色要改 Crew 结构 → 不适合"接口预留"
- LangGraph 是图式编排（StateGraph + checkpoint），加 Agent = 加 node + 加 State 字段 → 天然契合"加 Agent 不推倒"
- 用户已实操过 LangGraph（AAAZ Stage 4 B4/B5：双节点 + HITL），学习曲线可承受

---

## 五、收集 Agent 详情（当前唯一可用）

### CollectorAgent（采集）
- **输入**：`state.collector.{keyword, city, pages, filters}`
- **动作**：`import boss_cdp_raw.scrape_list()`（纯 Python API，非 subprocess）
- **输出**：`state.collector.{raw_jobs, stats, finished_at}`
- **风控适配**：scrape_list 内部已含（resolve_city / CDP 被动捕获 / 翻页 12-22s 随机 / code 37 识别）

### CollectorPersistAgent（落库）
- **输入**：`state.collector.raw_jobs`
- **动作**：复用 1.0 的 `import_boss_json.py` 解析规则（parse_salary / parse_tags / parse_district）写入 jobs 表
- **输出**：`state.collector.stats.persisted = {new, dup, skip}`

### 运行（隔 2-3 天"上班"一次）
```python
from agents import AgentState, build_default_pipeline

state = AgentState()
state.collector.keyword = "AI开发"
state.collector.city = "广州"
state.collector.pages = 2

orch = build_default_pipeline()
final = orch.run(state)   # 采集 → 落库 → (匹配/避坑占位)
print(final.collector.stats)
```

> ⚠️ 真实运行前置条件（《采集运行模式深度调研》结论）：
> 1. 电脑连手机**数据流量热点**（宽带 IP 仍被标记）
> 2. 先跑 `boss_cdp_raw.py --setup-chrome` 启动专用 Chrome（登录态持久）
> 3. **关闭 Clash/代理**（code 37 与代理出口 IP 相关，Issue #30 实证）

---

## 六、测试（接口契约守护）

`tests/test_agents.py` 8 个用例：

| # | 用例 | 验证 |
|---|---|---|
| 1 | state_namespace_isolation | 命名空间互不污染 |
| 2 | state_defaults | 默认 State 可实例化 |
| 3 | base_agent_is_abstract | 抽象强制（防漏实现） |
| 4 | concrete_agent_works | 实现类可执行 |
| 5 | orchestrator_tolerates_failure | 单 Agent 失败不中断流水线 |
| 6 | orchestrator_strict_mode | strict 模式立即抛错 |
| 7 | add_new_agent_without_breaking | 加新 Agent 不破坏现有 |
| 8 | real_agents_implement_contract | 真实 Agent 类接口齐全 |

**跑法**：`cd <repo>/core && python -m pytest tests/ -v`

---

## 七、待办（下一轮）

- [ ] MatcherAgent 实现（方向标记 + 基础过滤，读 1.0 config 权重）
- [ ] SkirmishAgent 实现（公司信息包 + 复制问坑文本 + DeepSeek 主动分析）
- [ ] 采集 Agent 真实跑一次（手机热点 + setup-chrome + keyword=AI开发 city=广州 pages=2）
- [ ] 展示层（可投列表卡片 + CSV/MD 导出）接 AgentState
- [ ] APScheduler 定时（默认关，用户手动开）
- [ ] LangGraph 化（架构定稿后按第四节迁移）

---

**代号：2026H2P | AI 投递助手 2.0 | 接口契约定稿 2026-08-26**
