# Workflow 可观测性报告

- Trial：`reward-v2-medium-MP02__4nN57ER__env`
- Task：`medium/MP02`
- Harness：`deepseek-harness`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（40 节点 / 39 边）
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

- 执行节点：40；执行边：39（observed=0，inferred=39）
- Execution Trace Graph：`observed`；temporal_next 边 39，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:dsh:lead:call_e49107200bc844caa95df394 -> tool:dsh:lead:call_77f1e1101d4a47d188b09871 -> tool:dsh:lead:call_73efe180a6af4b8ab12f4205 -> tool:dsh:lead:call_693ece1f5cf44876929ee6f1 -> tool:dsh:lead:call_436a90aaf8f741689f5b1d74 -> tool:dsh:lead:call_84f8687ba126478480e8777d -> tool:dsh:lead:call_82331b83bfd74371bfb2ae02 -> tool:dsh:lead:call_cc83478e2e2a438ebb702dcc -> tool:dsh:lead:call_50cffa62eaef464e904173aa -> tool:dsh:lead:call_52cfa4a0423c4c9386ea3159 -> tool:dsh:lead:call_8691eeb90ca84f44acdd4ac7 -> tool:dsh:lead:call_b07ff5871d6c4973a8b1e18d -> tool:dsh:lead:call_3b5c2e839cda44c0b59450f3 -> tool:dsh:lead:call_9c122ddaf97c4e27b09413f6 -> tool:dsh:lead:call_268af31cc2094524b8bec24c -> tool:dsh:lead:call_f868ac4d9951451d8463f473 -> tool:dsh:lead:call_3a3fd32adc2a4dd9b5c9a1e8 -> tool:dsh:lead:call_d5a79f8cb5c043dc9fcae193 -> tool:dsh:lead:call_507fc98b577d4d6fb816fc6c -> tool:dsh:lead:call_e9dd290f1ef54913bcf0aae4 -> tool:dsh:lead:call_f5f61982ace041fd88f42eba -> tool:dsh:lead:call_2a8c1bb7e29d4dfba51fb1ec -> tool:dsh:lead:call_70baa1063f7e453ca8320457 -> tool:dsh:lead:call_31cf9bc9cb844d2992d5c217 -> tool:dsh:lead:call_a3808af9b8a84b34a90cdbbe -> tool:dsh:lead:call_a37fdf581ac24f518c84dc85 -> tool:dsh:lead:call_fd3d08da900740b495a3b796 -> tool:dsh:lead:call_5dfbfba3a2c64b5aad2bbaee -> tool:dsh:lead:call_00c8d1e7a88f42ef86ab14a1 -> tool:dsh:lead:call_bed1722a2eea4408b4b7cb10 -> tool:dsh:lead:call_2e5750d4ae794cf6a7962369 -> tool:dsh:lead:call_9cd51b469cfe4efcadf99773 -> tool:dsh:lead:call_a437ad182baa462abe14ccbd -> tool:dsh:lead:call_fdee05527b4e42ff92aa8b6b -> tool:dsh:lead:call_fcf496f52e41416e95d1a805 -> tool:dsh:lead:call_1bcedce6b895486db6b58574 -> tool:dsh:lead:call_eebbe643a6da4917b9a6c73b -> tool:dsh:lead:call_09dc06ee33354622967fcf7b -> tool:dsh:lead:call_c56246b0def9415584ec5d74
- 关键路径耗时：1.325
- Makespan：365.514
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
