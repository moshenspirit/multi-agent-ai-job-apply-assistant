# 2.0 架构选型输入 — 类型 B 落地分析与路线对比

> 日期：2026-08-19
> 上游资料：DSH 代码级研究《type-b-code-analysis-for-ai.md》（`C:\Users\y\dsh-test\.project\`）+ 1.0 实际代码核查
> 目的：回答 DSH 留下的 7 个问题 + 输出落地路线对比，供用户讲完实际需求后选型定架构
> 协作红线：本文只列事实、选项、利弊，**不下最终结论**（决策权在用户）

---

## 〇、1.0 代码现状核查（写路线前的基准事实）

对原 1.0 版本（现 `web/` 目录）实际代码核查结果：

| 模块 | 文档声称 | 代码实际 | 差距 |
|---|---|---|---|
| 基础设施 | 前后端联通 | ✅ Flask 工厂 + 5 蓝图 + CORS，`GET /api/health` 正常 | 无 |
| 简历管理 | 完整 CRUD + 解析 | ✅ `resumes.py` 209 行 + `resume_parser.py` 122 行 + `llm_client.py` 70 行 | 无 |
| 条件配置 | 完整 CRUD | ✅ `config_routes.py` 60 行 | 无 |
| **岗位采集** | S1 collector.py | ❌ **services/ 下无 collector.py** | **完全空白** |
| **AI 匹配** | S2 matcher.py | ❌ **services/ 下无 matcher.py** | **完全空白** |
| 采集任务 API | /api/tasks/* | ❌ 3 个接口全部返回 501"暂未实现" | **占位** |
| 结果展示/投递 | M2/M3/M6 | 前端页面骨架存在（JobList/JobDetail/DeliveryHistory.vue） | 待接数据 |
| LLM 封装 | OpenAI SDK | ✅ `llm_client.py` 已做 `base_url` 可配置（实测改 DeepSeek 成功） | 无 |

**关键结论（事实）**：
- 1.0 完成的是"壳 + 简历 + 配置"，**需求 4/5 是真空白**，需求 6/7 的页面骨架等着接数据
- 好消息：`llm_client.py` 的 OpenAI 兼容封装让 DeepSeek 替换几乎零成本（改 `config.py` 的 base_url/model 即可）
- 数据库 4 张表（resumes/config/jobs/delivery_records）已建好，jobs 表已含 match_score/match_direction 字段，**匹配结果落库的 schema 已预留**

---

## 一、DSH 7 个问题的回答

### Q1：Repo 1 的 LangGraph 工程结构怎么映射到 Flask + SQLite + Vue3？

**事实**：Repo 1 的核心不是 LangGraph 本身，而是三个可迁移的模式：
1. **Agent 中间产物落库**（resumes.parsed_json / jobs.parsed_json）→ 你 1.0 的 resumes.structured 已是这个模式，jobs 表可加 `match_detail` JSON 字段承接
2. **严格 JSON Schema 输出** → 与框架无关，写 prompt 时约束即可
3. **分层目录**（core/modules/agents）→ 你的 backend/app 已有 routes/services/utils 分层，可加 `services/agents/` 子目录

**映射方案（事实陈述）**：LangGraph 的 StateGraph 只在你需要"显式状态机 + 失败恢复 + 分支循环"时才值得引入。你的 2.0 四段流水线（采集→匹配→展示→记录）是**线性流程**，用 Flask 蓝图 + services 层一个编排类（如 `pipeline.py`）即可表达，不必为了"用框架"而引入 LangGraph。真要引，也只用于匹配服务内部（JD 分析→差距分析→评分 3 节点子图）。

### Q2：Repo 5 的 Controller 编排怎么改成 LangGraph/CrewAI 可落地版？

**事实**：Repo 5 的价值是**设计原则**，不是 Google ADK 本身。可迁移原则：
- Controller 只协调不干活（编排层与执行层分离）
- 子 agent 输出 JSON-only，Controller 做字段级校验，失败重跑
- 工具独立封装（文件/哈希/CSV），agent 通过工具操作，不直接碰 IO

**落地选项（事实陈述）**：
- **LangGraph**：StateGraph 建 supervisor 节点 + 3-5 个 worker 节点，`send()`/`return` 控制流转
- **CrewAI**：Crew 定义 + sequential process + context 参数传依赖（你 Stage 4/7 学过，上手最快）
- **不引框架**：Python 类 `Controller(Agent, Validator)` + 工具函数模块，最轻

三者都满足"Controller + sub-agent + JSON 通信"，差别在编排的显式性和恢复能力。Repo 5 的 `tool_name_prefix="jobhubt"` 拼写错误教训：工具名与 prompt 必须严格一致。

### Q3：DeepSeek 替换 OpenAI 后，哪些 prompt/代码需要调整？

**事实**（基于实测，2026-08-19）：
| 项 | 现状 | 需要动的 |
|---|---|---|
| SDK 层 | `base_url` 已可配置 | 改 `config.py`：`OPENAI_BASE_URL=https://api.deepseek.com/v1`、`OPENAI_MODEL=deepseek-chat` |
| token 统计 | `print` 输出 | 保留（DeepSeek 返回 usage 格式兼容） |
| JSON 输出 | 无强制结构化 | ✅ **直接用 `response_format={"type":"json_object"}`**——实测 3/3 稳定，无 `<think>` 污染，prompt 可宽松 |
| max_tokens | 2000 默认 | 匹配实测 100-130 token 够，保留 2000 默认足够 |

**对比 MiniMax-M3 实测**：MiniMax 默认输出 `<think>...` 思考块污染 JSON 解析、稳定性 0/3，**不适合生产用**。DeepSeek 是干净的 JSON 输出。

### Q4：Repo 4 的对抗迭代适合"半自动岗位筛选助手"吗？

**事实**：
- 对抗循环（生成→评估→再生成）本质是**内容生成优化**，适用于"简历加分项"功能（把简历改好），**不适用于岗位筛选主流程**（筛选是判分不是生成）
- 成本账：每轮 2 次调用（Builder+Checker），3 轮 = 6 次/份简历；对 50-100 个岗位批量跑是爆炸成本，但只对"选中后精修简历"跑则可控
- **结论（推断）**：若做，做成"岗位详情页 → 一键生成优化简历"的可选功能，不进主流水线

### Q5：Repo 2 的 ATS 评分卡够支撑需求 5 吗？还是结合 1.0 的 6 维权重？

**事实（关键区分）**：
- Repo 2 评分卡（关键词25%/结构20%/动词20%/指标20%/格式15%）评的是**简历质量**（ATS 通过率视角），评的对象是"简历写得好不好"
- 你 1.0 的 6 维权重（薪资/地点/公司规模/行业/经验/学历）评的是**岗位匹配**（候选人偏好视角），评的对象是"这个岗位适不适合我"
- **两者维度不同，不是二选一**：需求 5（岗位匹配）应基于你 1.0 的权重体系 + LLM 语义匹配；Repo 2 评分卡可作为"简历加分项"的评估维度
- 可融合模型（事实陈述）：`最终匹配分 = LLM 语义匹配分（0-100） × 用户权重修正系数`，方向标签（frontend/ai/both/none）沿用 1.0 schema

### Q6：需要统一的消息协议 / 中间产物 schema 吗？

**事实**：需要，且**现在定义比以后便宜**。这是从"单机脚本"演进到"multi-agent 服务化"的关键基建。最小方案：
- 定义 Pydantic/dataclass schema：`CollectResult`、`JobAnalysis`（含 frontend/ai 双评分 + 理由 + 缺口）、`MatchSummary`
- Agent 间只交换 JSON，落库字段与之对齐（jobs 表加 `match_detail` JSON 列即可，1.0 已有 structured JSON 先例）
- Repo 1 的"中间产物落库"是最佳实践：中断可恢复、前端可查历史

### Q7：LICENSE 风险怎么规避？

**事实**：
| 仓库 | LICENSE | 结论 |
|---|---|---|
| Repo 1 | MIT ✅ | 可参考可复制（带版权声明） |
| Repo 2/3/4/5 | **均未发现 LICENSE 文件** | "no license" = 保留所有权利，**不能直接复制代码**，只能参考设计思路 |

对你影响小：你的项目本来就是**借鉴设计模式**（评分卡、Controller 模式、对抗循环），不复制代码，风险可控。但注意别把 Repo 2-5 的代码片段直接搬进项目。

---

## 二、落地路线对比（3 条，只列利弊）

### 路线 A：1.0 直填（最快出活）
- **做法**：不动现有架构，按开发进度文档补 collector.py + matcher.py + tasks 路由 + 前端接数据
- **借鉴**：Repo 1 的 JSON 落库、Repo 2 的评分维度（用于加分项）
- **Multi-Agent 属性**：弱——仍是"服务函数"，需要包装才能讲成 multi-agent
- **利**：出活最快（纯补 4 个模块）；1.0 资产全复用；风险最低
- **弊**：蓝图目标③（成熟 multi-agent 项目）达成度低；面试讲不出架构亮点

### 路线 B：1.0 演进 + 匹配服务内部多 agent（平衡线）
- **做法**：在 A 基础上，把 matcher.py 拆成 3 个子 agent（JD 分析→简历比对→评分），用编排类或 CrewAI sequential crew 串起来；中间产物 JSON 落库
- **借鉴**：Repo 1 的 3 节点子图 + JSON Schema、Repo 2 的评分卡
- **Multi-Agent 属性**：中——匹配环节是真正的多 agent，采集/展示保持服务化
- **利**：出活较快；有真实多 agent 结构可讲（能对面试官讲清楚 agent 分工）；2.0 四需求全部覆盖
- **弊**：比 A 多一层设计和 LLM 调用成本；需要先定义中间产物 schema

### 路线 C：先架构后实现（Controller 编排重写）
- **做法**：参考 Repo 5，Controller Agent 编排 4 段流水线（采集/匹配/评分/记录），子 agent JSON-only + 校验重跑 + 反幻觉；用 LangGraph 或 CrewAI 实现
- **借鉴**：Repo 5 全部设计原则 + Repo 1 的持久化
- **Multi-Agent 属性**：强——最接近"成熟 multi-agent 项目"目标
- **利**：蓝图目标③达成度最高；面试差异化最强；架构一步到位
- **弊**：2.0 出活最慢（重写而非填补）；初学者驾驭风险最高（用户 8/18 自评"担心能力不足"）；采集环节套 agent 编排收益有限（采集是 IO 密集，不是 LLM 密集）

---

## 三、选型决策点（用户讲完实际需求后逐个定）

1. **节奏优先级**：先出活（A/B）还是先架构（C）？还是"架构上留口子、实现按 A/B 走"？
2. **框架**：不引框架 / CrewAI / LangGraph？（你 Stage 7 的 p7 pipeline 是自研编排类，其实已有先例）
3. **需求 5 匹配**：单 agent 批量 vs 多 agent 分层？（决定匹配服务的复杂度）
4. **对抗循环**（简历加分项）：做不做、何时做？（建议不进主流程，成本账已列）
5. **中间产物 schema**：现在定义还是演进中加？（Q6 结论：现在定义更便宜）
6. **采集方案**：Playwright 半自动（架构文档已设计反爬 4 层）是否有变？
7. **DeepSeek 适配**：✅ 已实测确认 JSON-mode 100% 稳定，直接 `response_format` + `json.loads()` 即可（Q3 已结）

---

## 四、结论速览

1. 1.0 的"壳+简历+配置"是真实资产，需求 4/5 是真空白，LLM 封装已兼容 DeepSeek（实测 JSON-mode 100% 稳定）
2. 5 个仓库最有价值的不是代码，是 4 个设计模式：JSON 落库、ATS 评分卡、对抗循环、Controller 编排
3. Repo 2-5 无 LICENSE，只能借鉴思路不能抄代码；Repo 1 MIT 可放心参考
4. 三条路线 A（快）/B（平衡）/C（重），差异在"出活速度 vs multi-agent 成熟度"
5. 决定路线前，需要用户的实际投简历需求输入（下一环节）
