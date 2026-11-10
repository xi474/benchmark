# Workflow 可观测性报告

- Trial：`glm53low-r3-opencode-medium-MP06-repair`
- Task：`medium/MP06`
- Harness：`opencode`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（22 节点 / 21 边）
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

- 执行节点：22；执行边：21（observed=0，inferred=21）
- Execution Trace Graph：`observed`；temporal_next 边 21，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:opencode-root:call_7f3ae322150342beb73411cc -> tool:opencode-root:call_087b521bd98c42efae217287 -> tool:opencode-root:call_7cd209e25e1a4889881a7c31 -> tool:opencode-root:call_9c8cf8357322458b864440ae -> tool:opencode-root:call_f54e3e62429f463896eab448 -> tool:opencode-root:call_3e1731b72a3f4731bbccf9e2 -> tool:opencode-root:call_0a7cb4c4eb0f4911b3e59f5e -> tool:opencode-root:call_a4d12764abf14436a792c757 -> tool:opencode-root:call_9a6ec3c097004d48ab79f6c9 -> tool:opencode-root:call_8ea64e469a9243cf91334632 -> tool:opencode-root:call_d6ec326dab134f7da281b540 -> tool:opencode-root:call_c8584925f66649ceb1341d8e -> tool:opencode-root:call_b5a4a5f94aeb48f7ac96b452 -> tool:opencode-root:call_c6d4b7b312d845d0b571d893 -> tool:opencode-root:call_c8920e88f6994887bedb6de5 -> tool:opencode-root:call_4495e198f29343ee8251ac87 -> tool:opencode-root:call_bc5c275846374a67ba8dcddd -> tool:opencode-root:call_c7627c9f08df4cf6a82f2752 -> tool:opencode-root:call_56f7990ebf0348d8868d13c7 -> tool:opencode-root:call_bcc897be311b449ab9ef4b53 -> tool:opencode-root:call_24e4e726c9d44797a58177ef
- 关键路径耗时：0.696
- Makespan：372.886
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
