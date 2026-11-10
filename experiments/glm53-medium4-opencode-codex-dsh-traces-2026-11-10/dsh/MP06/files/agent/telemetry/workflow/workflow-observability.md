# Workflow 可观测性报告

- Trial：`reward-v2-medium-MP06__LNcxhEs__env`
- Task：`medium/MP06`
- Harness：`deepseek-harness`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（36 节点 / 35 边）
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

- 执行节点：36；执行边：35（observed=0，inferred=35）
- Execution Trace Graph：`observed`；temporal_next 边 35，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:dsh:lead:call_7c8fd9f9ee86412d89c60a12 -> tool:dsh:lead:call_afa17dd26a784c87be6d4328 -> tool:dsh:lead:call_bd166967be49473fb7635cd4 -> tool:dsh:lead:call_45cb53459c78493aa2073f2f -> tool:dsh:lead:call_b23b7d85b88440e69cc46e80 -> tool:dsh:lead:call_b8bc34b7f56845e7ac8cffb2 -> tool:dsh:lead:call_78d19c0e176e4bd19dde784e -> tool:dsh:lead:call_4f789930b1c84a4ea30c626f -> tool:dsh:lead:call_5f91fec57042498da57fd33e -> tool:dsh:lead:call_81022fadf2754c58af739548 -> tool:dsh:lead:call_ed5df9ebe54d4957b1173732 -> tool:dsh:lead:call_027f24f67f374556a4881a36 -> tool:dsh:lead:call_06ff303cb2cb4c0793a19fc7 -> tool:dsh:lead:call_7b95552079814e55acd3fa8f -> tool:dsh:lead:call_cba80733b26a4bbea043a6db -> tool:dsh:lead:call_cba461a215c147c5822a7b55 -> tool:dsh:lead:call_192dbcada17b40d2832d93f3 -> tool:dsh:lead:call_612b5e8264dc41c9b30eecd0 -> tool:dsh:lead:call_4cef547715824656962b50dc -> tool:dsh:lead:call_beacc5811131453fa2f09150 -> tool:dsh:lead:call_acdc9d492a8c4dce84e8bbb9 -> tool:dsh:lead:call_919c14eaacd04b6eaec38500 -> tool:dsh:lead:call_5b255afb28ba4d0bb17a4878 -> tool:dsh:lead:call_8ce5ce9f4da44e2c80dbc89a -> tool:dsh:lead:call_8db6b31c62e240f98e0eb792 -> tool:dsh:lead:call_07a8f0a826d3466da42ba9f8 -> tool:dsh:lead:call_8e523f0ab9bb47e894f06508 -> tool:dsh:lead:call_e5554c645c3d43d6ab4beabb -> tool:dsh:lead:call_c5907802f62641fcb17f4d62 -> tool:dsh:lead:call_286c440b3ca04965a2bd35a1 -> tool:dsh:lead:call_54398711f08a497fafb2c229 -> tool:dsh:lead:call_d3790ff6d97d4aac966bc2ce -> tool:dsh:lead:call_53aef9be16ea4a04a3b707d5 -> tool:dsh:lead:call_4c6e411f647941e9b999ec41 -> tool:dsh:lead:call_128893a440854e0280766d78
- 关键路径耗时：1.221
- Makespan：205.957
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
