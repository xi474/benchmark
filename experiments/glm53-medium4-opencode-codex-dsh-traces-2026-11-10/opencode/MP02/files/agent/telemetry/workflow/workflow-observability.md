# Workflow 可观测性报告

- Trial：`glm53low-r3-opencode-medium-MP02-repair`
- Task：`medium/MP02`
- Harness：`opencode`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（19 节点 / 18 边）
- Agent Topology：已观察到（1 Agent / 0 子 Agent）
- Data Dependency DAG：未观察到（0 artifact / 0 message）

## 2. 规划证据

- planning_level：`P0`
- plan_source：`not-observed`
- 证据事件：无
- Plan 快照数：0
- Plan revision 数：0
- 未观察到模型计划的原因：Only root-Agent/model/tool execution events were observed; no local control decision or plan exists.

> 静态 LangGraph / Strands Graph 属于 Harness Control DAG，不是模型自主 Plan DAG。
> 工具调用顺序和 Execution DAG 不能反推模型计划。

## 3. 执行与并行

- 执行节点：19；执行边：18（observed=0，inferred=18）
- Execution Trace Graph：`observed`；temporal_next 边 18，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:opencode-root:call_d35b066fe654475abad8f2b1 -> tool:opencode-root:call_674caf98cd8e43b18f63c3cb -> tool:opencode-root:call_a48d2fed2b1641e6a6e31b70 -> tool:opencode-root:call_6cae98e4f6fb4485954af86a -> tool:opencode-root:call_2d12948094a94635890c4a2a -> tool:opencode-root:call_60d0addfe81b4cf19420ab08 -> tool:opencode-root:call_5a3eb78457e54658a191eaa0 -> tool:opencode-root:call_62ec7a700bc5437d828753ad -> tool:opencode-root:call_b59eb51755db41b9872193d6 -> tool:opencode-root:call_ecb656f966e1438b96c74bc8 -> tool:opencode-root:call_077241befc044bcc8a94f21e -> tool:opencode-root:call_2226b9e1b5584cdb8f3ac741 -> tool:opencode-root:call_85fe2979c16446af98cc8958 -> tool:opencode-root:call_89b1762f3b1246e697e6ffca -> tool:opencode-root:call_3cbcebd6962647cfa6409a20 -> tool:opencode-root:call_4a991cd6bed246ff94bd439a -> tool:opencode-root:call_5f477da1731a4b0b8196e80e -> tool:opencode-root:call_3be3b20c9d7349fdbfd50528
- 关键路径耗时：0.986
- Makespan：809.55
- 子 Agent 并行宽度：0
- 委派：0；handoff：0

## 4. 分支、重试、取消、汇合

- 跳过节点：无
- 重试节点：无
- 取消节点：无
- 剪枝分支：无
- 汇合等待：None

## 5. Workflow 一致性

| 对比 | 状态 | 计划节点 | 执行节点 | 计划未执行 | 执行未计划 | 节点重合比 | 边重合比 |
|---|---|---:|---:|---|---|---:|---:|
| Provided vs Execution | not_observed | - | - | - | - | - | - |
| Harness Control vs Execution | not_observed | - | - | - | - | - | - |
| Observed Model Plan vs Execution | not_observed | - | - | - | - | - | - |

## 6. 结论边界

- **observed**：事件或图中直接存在，且带 evidence_event_ids。
- **inferred**：没有直接依赖证据时按时间顺序补的边，confidence=0.3，不能当真实依赖。
- **not_observed**：没有数据/能力；不能填 0。
- 本报告不把静态 Graph 写成模型计划，也不从工具调用顺序推断模型规划。
