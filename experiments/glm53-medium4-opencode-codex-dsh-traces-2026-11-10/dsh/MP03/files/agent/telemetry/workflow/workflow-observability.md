# Workflow 可观测性报告

- Trial：`reward-v2-medium-MP03__xXUjXJC__env`
- Task：`medium/MP03`
- Harness：`deepseek-harness`
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
- 关键路径：tool:dsh:lead:call_940bbc62bc9840e99b0a207d -> tool:dsh:lead:call_b3f020d213fa4fdabb9a477a -> tool:dsh:lead:call_881044b85e4044a0a69a406d -> tool:dsh:lead:call_80f913e70deb44ca988ed8ae -> tool:dsh:lead:call_be8b576c569f44f6b3312aee -> tool:dsh:lead:call_1d6e99f168c14f598922e9d6 -> tool:dsh:lead:call_d23f8e5b991344aa9b4ac926 -> tool:dsh:lead:call_4a4c2881e15c4f7ea6a87207 -> tool:dsh:lead:call_f31e852928e24e83b55705d7 -> tool:dsh:lead:call_49f78184922d4ad785dc90ac -> tool:dsh:lead:call_12f9dfa55a304ef1846023d8 -> tool:dsh:lead:call_fdef7f66a2e24cccba94d016 -> tool:dsh:lead:call_59d3d552213b44e3bcfc2783 -> tool:dsh:lead:call_fe9da98bc8e34a8f9c3ad3c0 -> tool:dsh:lead:call_1749d8c3a8f14a28a6ea7c8e -> tool:dsh:lead:call_e5051b7dfd76435ca8ad7a73 -> tool:dsh:lead:call_3d5e61ad881b4e8b8f093970 -> tool:dsh:lead:call_50776f9e84ee49e9973706f7 -> tool:dsh:lead:call_de92c7127c654e789d420043 -> tool:dsh:lead:call_12d62ead1ead436997f532f4 -> tool:dsh:lead:call_241d71e426e54961bcd1efdd -> tool:dsh:lead:call_63a982ea713e4c9989a421c2 -> tool:dsh:lead:call_8d39132e7e8e4d9b89ad339a -> tool:dsh:lead:call_506cf165ca454a46b2b87975 -> tool:dsh:lead:call_ba5c1a29e11f42ec981685ce -> tool:dsh:lead:call_7f409bad595b4a4caf84946d -> tool:dsh:lead:call_478c8b52b5594ccbabc75a8a -> tool:dsh:lead:call_a321e57ba3114ad7b7738ff3 -> tool:dsh:lead:call_ac998b4d271941fbaf87112b -> tool:dsh:lead:call_4fc6905e1e264973be00a531 -> tool:dsh:lead:call_fb3b7bcd9f004eac90ea4349 -> tool:dsh:lead:call_46418022ee0743039dd42968 -> tool:dsh:lead:call_238b125ebd1845aeb13de1e0 -> tool:dsh:lead:call_b145f8e740e44e40b18b1c23 -> tool:dsh:lead:call_104d77d59403474b801e848f -> tool:dsh:lead:call_870e864defc84436be92847c -> tool:dsh:lead:call_72d17b20eba34886bc7564cf -> tool:dsh:lead:call_40db999407ff4d7ea21243a0 -> tool:dsh:lead:call_35a3d2127c484859b4ecec93 -> tool:dsh:lead:call_d492b97e3cf3436690670297 -> tool:dsh:lead:call_81111d237af74aedac816b23 -> tool:dsh:lead:call_b3b6ba6af3b84f22a4c7e720 -> tool:dsh:lead:call_07d378c47072431080f7675b -> tool:dsh:lead:call_3c64e29eceb34692adf5ef9c -> tool:dsh:lead:call_e96b4d8f0ad24f88ab90c197 -> tool:dsh:lead:call_6126b5630cc6483d8aed43c0 -> tool:dsh:lead:call_d5ad8e556a4d47aebc4a95eb -> tool:dsh:lead:call_2ff5673f99fe4e80bcb9ca91 -> tool:dsh:lead:call_fea6606e03104722aced22e5 -> tool:dsh:lead:call_4903374ce3e3415ebea3f0c8 -> tool:dsh:lead:call_3acfb4a4fec8402bb24ad871 -> tool:dsh:lead:call_8e4caaff2ea24100ac90f254
- 关键路径耗时：2.02
- Makespan：363.533
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
