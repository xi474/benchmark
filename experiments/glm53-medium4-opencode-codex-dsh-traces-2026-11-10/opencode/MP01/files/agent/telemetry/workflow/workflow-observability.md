# Workflow 可观测性报告

- Trial：`glm53low-r3-opencode-medium-MP01-repair`
- Task：`medium/MP01`
- Harness：`opencode`
- 规划等级：`P0`
- 规划来源：`not-observed`
- 是否观察到模型显式计划：否

## 1. 六类图状态

- Provided DAG：未观察到（`No Provided DAG was supplied for this trial.`）
- Harness Control DAG：未观察到（`No Harness Control DAG was declared.`）
- Observed Model Plan DAG：未观察到（`No explicit model-created plan event was emitted.`）
- Execution DAG：已观察到（53 节点 / 52 边）
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

- 执行节点：53；执行边：52（observed=0，inferred=52）
- Execution Trace Graph：`observed`；temporal_next 边 52，均为 inferred/low confidence，不是任务依赖。
- Execution Dependency DAG：`not_observed`；observed dependency 边 0，inferred dependency 边 0。
- 关键路径：tool:opencode-root:call_41c1c3d8d80047b4939f2afa -> tool:opencode-root:call_6b6944e9eb9e478786664544 -> tool:opencode-root:call_386ea07649cb480689faa668 -> tool:opencode-root:call_cedaddff18db49eaa61e8aab -> tool:opencode-root:call_e3d9ed2b0e0646f5b500b0b9 -> tool:opencode-root:call_00a97c28824b4d7ebee98738 -> tool:opencode-root:call_9a48f54ce5254c9bbf321a67 -> tool:opencode-root:call_73229fc80dc94399b0263fd4 -> tool:opencode-root:call_d75d07f64dd44e86b81dea7c -> tool:opencode-root:call_185fb6d5d21047f788a714a7 -> tool:opencode-root:call_1b63f6c9ed8a40c7b71f51fb -> tool:opencode-root:call_471960b05e144309ba9601a8 -> tool:opencode-root:call_bc15f3bf47794124a28b3311 -> tool:opencode-root:call_8ac42b245d834f0e8da3d45b -> tool:opencode-root:call_33bdfa3363004853bf31f596 -> tool:opencode-root:call_02958888ff5a428581a11d13 -> tool:opencode-root:call_d5582f2337d248aeb1cfce83 -> tool:opencode-root:call_7131ba9fd2e2471bbe2b3b2a -> tool:opencode-root:call_07be97b6ba484beca5908728 -> tool:opencode-root:call_aea8be50b6fd446781641366 -> tool:opencode-root:call_1a0ba8bd290044f9b1e2e847 -> tool:opencode-root:call_7a01aa3835824b0fb0c273ca -> tool:opencode-root:call_a5bbe9e56d194f22bbc54bb6 -> tool:opencode-root:call_12115415f65546a9a6a8d0d0 -> tool:opencode-root:call_95597542988043d481517a6a -> tool:opencode-root:call_f63673a5acd1413bb1efdb23 -> tool:opencode-root:call_d9a1c52732e34e5ea818b3b7 -> tool:opencode-root:call_4c59b522e82a49cc94023c19 -> tool:opencode-root:call_83cbb464250946f2ba36043f -> tool:opencode-root:call_109bdadc040f4c248da6cfa4 -> tool:opencode-root:call_7676756cc78842cc864484ec -> tool:opencode-root:call_448eaf4ad0f0455b828c39cd -> tool:opencode-root:call_9146fcc83d9145b4b20ac889 -> tool:opencode-root:call_7a59afd10f864dca8e66fe6b -> tool:opencode-root:call_ac9a408295f44ccaa62a6029 -> tool:opencode-root:call_ee2e84bb2c95494dac4c59f6 -> tool:opencode-root:call_165bd7be68e54d7192a10648 -> tool:opencode-root:call_0e14e0eee9ed4f05bbd3d5e6 -> tool:opencode-root:call_6f3a3181325c49efb073670c -> tool:opencode-root:call_06805d9fff874c9bb6b8ed15 -> tool:opencode-root:call_95d3cb41fa1b48a9aac3ef08 -> tool:opencode-root:call_2eb9462f13274394946359de -> tool:opencode-root:call_2212a9116aff462ba4adeec4 -> tool:opencode-root:call_750d00d7ecd5466dabbd0923 -> tool:opencode-root:call_e29188f091db4abb87293ff9 -> tool:opencode-root:call_769ae93140094a4d8c1eb37a -> tool:opencode-root:call_e3845c8cc43348e2b4dfa4d7 -> tool:opencode-root:call_efa34efd225342878e083de6 -> tool:opencode-root:call_0bcc6c0fe3ef43949ee7cb68 -> tool:opencode-root:call_42f00513b9e4488da0d7bd39 -> tool:opencode-root:call_8d454af262f448c7b0e24d0c -> tool:opencode-root:call_44727517f85b4a2c991d15b7
- 关键路径耗时：1.756
- Makespan：760.118
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
