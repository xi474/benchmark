# Workflow 可观测性报告

- Trial：`reward-v2-medium-MP02__JHr5hjn__env`
- Task：`medium/MP02`
- Harness：`codex`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（1 节点 / 0 边）
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

- 执行节点：1；执行边：0（observed=0，inferred=0）
- Execution Trace Graph：`observed`；temporal_next 边 0，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：agent:codex:01a1c384-dabd-7bb3-b8b3-7574c895b2d8:1
- 关键路径耗时：0.0
- Makespan：None
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
