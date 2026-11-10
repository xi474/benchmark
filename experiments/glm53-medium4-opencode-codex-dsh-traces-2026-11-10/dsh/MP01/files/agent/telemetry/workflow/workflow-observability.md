# Workflow 可观测性报告

- Trial：`reward-v2-medium-MP01__wvvSBTZ__env`
- Task：`medium/MP01`
- Harness：`deepseek-harness`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（38 节点 / 37 边）
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

- 执行节点：38；执行边：37（observed=0，inferred=37）
- Execution Trace Graph：`observed`；temporal_next 边 37，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:dsh:lead:call_a960ba5a6f3d49419804f995 -> tool:dsh:lead:call_4705e72ae7a4404b89b60020 -> tool:dsh:lead:call_8440e6c1d3af4694bed75f48 -> tool:dsh:lead:call_49631a0aab8d454c8e92e037 -> tool:dsh:lead:call_fbcbdedc047146afa1d8d95a -> tool:dsh:lead:call_3a2662236dda409588005945 -> tool:dsh:lead:call_c47b8f0bb3e74c44850d8035 -> tool:dsh:lead:call_6226ce5fd6fb413cb9967dc6 -> tool:dsh:lead:call_53df5c9ae6d44af3aa60fe8f -> tool:dsh:lead:call_5faf36cf07054fbbaf78dc9f -> tool:dsh:lead:call_bbe41699fe0c4ef390d4aa18 -> tool:dsh:lead:call_5d5e383d77b74103b52905c1 -> tool:dsh:lead:call_363e9e1628af4aa491190f3a -> tool:dsh:lead:call_a89313334a5f4b6da5fb2fa5 -> tool:dsh:lead:call_60ecd5b776384b0096f8cd0d -> tool:dsh:lead:call_d09e6abcbf714a7fab6205a3 -> tool:dsh:lead:call_24add46eda7e438aa0c4f72e -> tool:dsh:lead:call_1ce59bd6b8c143d78f943be0 -> tool:dsh:lead:call_fe26680bd0a6439f9449af31 -> tool:dsh:lead:call_6364f59a2eca46ca9927178c -> tool:dsh:lead:call_7541cd023a9a49688e68a262 -> tool:dsh:lead:call_449330695aa240759104e751 -> tool:dsh:lead:call_ed904c8c9bdf41aeabde3a9b -> tool:dsh:lead:call_88dcd89fc86a427da9771656 -> tool:dsh:lead:call_c655fed1370f4f53b6e71d19 -> tool:dsh:lead:call_9492ba1096bf4a20bdcb3e7c -> tool:dsh:lead:call_fb01771874cf4bb79eba2c0d -> tool:dsh:lead:call_b146bee657da43a28b6d8220 -> tool:dsh:lead:call_d04b584b35204be4b34f9735 -> tool:dsh:lead:call_d1ea119b5d7a450e98497896 -> tool:dsh:lead:call_d2f9484aa67947d99447d56d -> tool:dsh:lead:call_af3e71e1d0a442ceb21c16bf -> tool:dsh:lead:call_cc4bec0d41974989977bd0aa -> tool:dsh:lead:call_ac8b09a03a514c25927db897 -> tool:dsh:lead:call_3c33e95600fb41118cc3791d -> tool:dsh:lead:call_842e6ed25ac54aeea1d3ea5d -> tool:dsh:lead:call_caf48abbabf145c7b82c22c2
- 关键路径耗时：1.789
- Makespan：275.0
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
