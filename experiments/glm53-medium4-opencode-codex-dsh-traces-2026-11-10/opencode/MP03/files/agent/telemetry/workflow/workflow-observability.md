# Workflow 可观测性报告

- Trial：`glm53low-r3-opencode-medium-MP03-repair`
- Task：`medium/MP03`
- Harness：`opencode`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（59 节点 / 58 边）
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

- 执行节点：59；执行边：58（observed=0，inferred=58）
- Execution Trace Graph：`observed`；temporal_next 边 58，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:opencode-root:call_4c8e54ae05c746829620cfba -> tool:opencode-root:call_cc57ea6e2fcd4a8fb0a93da8 -> tool:opencode-root:call_a1a8c5db643b438faf72882f -> tool:opencode-root:call_1b52cfbb4a5d4bfba6811ce1 -> tool:opencode-root:call_a8a8dfd134e44db68e111a39 -> tool:opencode-root:call_7c431d50149d4d4993d4fc33 -> tool:opencode-root:call_a8c612180b7a4f989d7dd32c -> tool:opencode-root:call_c7dfe5759cdc4181a9b26ba0 -> tool:opencode-root:call_f38be1ef59864aa5ba3d205f -> tool:opencode-root:call_fb106964516344909b0bba7d -> tool:opencode-root:call_781981d3b1844b3f9c40d992 -> tool:opencode-root:call_1d71a34ac3d04ce785a2b404 -> tool:opencode-root:call_a99c0b700f814f1da8dea667 -> tool:opencode-root:call_bc6f47c39ba740748b333576 -> tool:opencode-root:call_54a865035cf549a980f31fc7 -> tool:opencode-root:call_b7706a4df1344ebcab7d2576 -> tool:opencode-root:call_a2373aefa68140e8905313ed -> tool:opencode-root:call_2787726d4b6b49f385084840 -> tool:opencode-root:call_f67f099f9cb84ff3b5d95cc0 -> tool:opencode-root:call_bcf60a28aa0d43f58f20eeb0 -> tool:opencode-root:call_24111d5ee7af47f683e1141f -> tool:opencode-root:call_8b90bc5165c544bd86f9173f -> tool:opencode-root:call_963024f763af4c1f9f7b3b2e -> tool:opencode-root:call_e341720ffab54c51874ff4fa -> tool:opencode-root:call_d90bd0e7180e4780a8254f43 -> tool:opencode-root:call_d424522d92b54c68baaa512c -> tool:opencode-root:call_66b13d46d42341d88b292d3d -> tool:opencode-root:call_c1e677a408594075834ce5eb -> tool:opencode-root:call_6ea3444dd00d4c039b2c85e8 -> tool:opencode-root:call_9589299ac02f4befa7398060 -> tool:opencode-root:call_0c7dc6d69dd44517b6d38c82 -> tool:opencode-root:call_db389389acb54bd3a98c1c56 -> tool:opencode-root:call_68620154953e4b758bf3a770 -> tool:opencode-root:call_8d97542f758743fabe7a5c51 -> tool:opencode-root:call_1eba3242a7ff4c4c88626ee6 -> tool:opencode-root:call_ba87a393ba4b46d1858cb2bd -> tool:opencode-root:call_916e44a2fa5948c8817e65ba -> tool:opencode-root:call_4b458f89025041d585421fa1 -> tool:opencode-root:call_e235f8e11a1e401988bac1cc -> tool:opencode-root:call_0348dc7d2750460690b4c65b -> tool:opencode-root:call_efc9140b8d1a48b9ad5051ff -> tool:opencode-root:call_df3717cd7cc845409226ec48 -> tool:opencode-root:call_609eab45b5084579b702ffb0 -> tool:opencode-root:call_b9c95faf919749d4a3ff7c66 -> tool:opencode-root:call_a72b16eda6df45e0a40f8e54 -> tool:opencode-root:call_2ab3ca386b8b478c840a452a -> tool:opencode-root:call_4eaea8600ac040b99d039225 -> tool:opencode-root:call_d233181a79644679a18c2041 -> tool:opencode-root:call_36bbea975d164af08835c79b -> tool:opencode-root:call_ba814360e35544cb9d16ee5e -> tool:opencode-root:call_8ad5e5f31b1a472aadff5c2f -> tool:opencode-root:call_a0ccf3e7381f42d1a8316d9e -> tool:opencode-root:call_b68b30cbe88d4232bff353a9 -> tool:opencode-root:call_05fbdbcbb8674fe4a8bd2c11 -> tool:opencode-root:call_383bef3a42ba4d40b31b8bcd -> tool:opencode-root:call_b0ba2407a59945a19e122467 -> tool:opencode-root:call_d2bf3a1e12f343e6b094b4ac -> tool:opencode-root:call_6041eabff9fb400cbcd4fad5
- 关键路径耗时：2.669
- Makespan：899.598
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
