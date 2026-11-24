# SemanticParallel 的准确率与 Reward 改进方案

2026 年 11 月 23 日 · Upstream59 · 供方案评审

## 结论

建议按**协议故障降级 → 根工作区整体验证 → 原生局部编辑**的顺序实施。协议降级先保证模型拿得到工具并能开始写实现。根工作区的构建、整题检查与定向返修最接近严格通过的主要缺口。局部编辑能降低返修摩擦，可以独立评估它对 token、耗时和准确率的影响。

首轮 59 题中，SP 有 50 题通过公开检查，25 题严格通过。采用公开检查触发的重放策略后，分别为 56 和 28 题。Codex、DSH、Nanobot 严格通过 38、36、32 题，其领先主要来自严格通过加分。195 次成功分支交付的回执仅覆盖文件完整性。因此值得优先提高**拿到分支产物以后，根 Agent 找到集成错误并继续修好的概率**。历史差额是选题依据，机制的净收益需要单独测量。[Upstream59 机制差距](sp-mechanism-gap-analysis-20261123.md) · [逐题评分](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

## 1. 协议失败后让业务继续执行

<a id="source-line-13"></a>
### C069 的直接原因

首轮前两代握手分别在第 2、4 步成功。第 5 步安排第 3 代握手，随后的第 6–128 步全部在重试 `report_frontier_state`。123 条拒绝都是 `done_add.0` 超长。当前工具 schema 的上限为 160 字符，原始失败请求里的长度为 182、235 或 238 字符。第一次拒绝发生在根任务启动约 22.7 秒后，最后一次约 646.7 秒后。该代握手始终没有提交。根会话没有写实现、执行 Shell 或启动分支，最后触及 128 步上限，正式 API 为 **0/9**。重放中出现过一次 `goal` 超长，流程随后恢复，最终为 **9/9**。这两个原件说明问题集中在持续拒绝后的恢复路径。[C069 首轮 trace](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/trace.jsonl) · [归档 trace 索引](evidence/semserve-trace-metrics.json) · [工具参数限制](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L646)

当前源码能解释事件链。握手待提交时，`_model_tool_schemas` 向模型暴露单一报告工具。格式修复计数检查“是否恰好调用了这个工具”，然后清零。参数校验在之后执行，返回 `not_executed`。只有成功回执才清除待提交状态。业务进度检测跳过全为控制工具的批次。于是调用形式正确、参数反复无效的响应每轮都能进入相同状态。当前注册表已能返回字段、实际长度和上限，诊断信息可以直接复用。源码定位以本地提交 `109a65444b3d4884fe92ec9e1c543b85df34e95d` 为准，运行行为以归档为准，部分挂载覆盖文件与当前文件的字节哈希有差异。[报告工具暴露](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/runtime.py#L4643) · [格式修复计数](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/runtime.py#L882) · [参数校验反馈](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/registry.py#L205) · [成功提交条件](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L712) · [业务进度判断](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/progress_recovery.py#L33)

预算也要按阶段读取。冻结计划的 300 秒是 `selfcheck_budget_seconds`。C069 首轮从未进入自检，终止证据是 `Agent exceeded 128 steps`。此前报告已把这一处预算表述更正。[C/MS 冻结计划](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/experiment_plan.json#L207)

### 建议改动

1. **给同一代握手加独立失败计数。** 按代记录报告格式错误、参数校验拒绝和拒绝原因。对相同参数错误，用字段路径与约束类别作为签名，忽略每次生成的具体文本。首次拒绝给一条针对性反馈，例如 `done_add` 填短 ID，或在无可报告变化时填空数组。正常提交时清零。仅提示重试的效果可以靠已有 trace 和离线回放检查。
2. **到限后原地回到根业务工具。** 起始阈值建议为同代相同签名第 2 次拒绝，或同代合计第 3 次失败。届时显式记录为本次 trial 的串行降级，撤销待提交的报告授权及对应并行提议，停止为该 trial 调度新握手。恢复同一根会话的读写、Shell 和完成工具，带上已验证的结果、现有工作区及剩余预算。已有分支在安全边界按原交付规则结算，已合并版本继续使用，未验证产物保持隔离。完成仍通过 Output Guard。
3. **记录能验证恢复的事件。** 至少有握手代数、字段与拒绝签名、收到的失败次数、采用的退出原因、下一次实际暴露的工具、第一次成功业务修改及最终验证结果。将 C069 的旧请求序列做成脚本化回放，验证两个正常报告仍可提交，第 3 代触及阈值后下一轮可调用业务工具。补充一次失败后正常恢复、字段轮换、已有分支及恢复后完成检查失败的用例。

这项改动的直接验收是**在错误发生处恢复开始做题的能力**。C069 的独立重放说明任务可以完成，原地降级后的正确率仍待试验。正常握手、多分支合并和资源开销应一起纳入回归。

## 2. 在同一个根工作区闭合修改、重建与整题验收

### 覆盖缺口

现有根集成检查点已经提示模型检查分支产物、实现入口并运行聚焦测试，`finish_task` 已有公开检查、候选自检及同版本的最终复验。它们可以成为改动的入口。C039 和 MS11 两轮均没有记录到运行时根公开检查回执，API 分别为 **0/10、1/10**。C068 和 MS41 已经过公开检查及串行自检，API 仍仅 **8/9、5/11**。前一类需要根集成阶段及时拿到可操作的失败，后一类需要检查组合约束及干净环境可再现性。首轮进入自检的 50 题，开始自检的时点中位数约为各自完成用时的 **70.5%**，其中 7 题记录自检预算耗尽。[已审计 trace 数据](evidence/strict-trace-audit.json) · [根集成检查点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L815) · [公开检查与同版本复验](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L16)

### 建议改动

1. **把合并后的第一轮可运行性检查接进根执行。** 根保留同一个工作区和上下文。合并后核对交付文件与根负责的入口，按冻结的题型配置取得公开构建和检查入口。组件存在时先运行必要的公开组件检查，再按题面要求重建产物并运行整题检查。C/MS 用已登记的 `public_check.py` 或任务定义的 `run_all.py --check`，MP/N 使用各题登记的 `check.py`。分支没有工作产物的题在根入口或候选产物就绪时进入相同流程。所有命令取自本题公开定义，依赖顺序随任务配置冻结。
2. **把可定位的失败送回同一个 Agent。** 返回阶段、失败组件或公开用例、退出码、截取后的错误、受影响的入口及当前源码版本。模型可直接修改这个版本。重跑同一失败检查需有相关源码、入口或依赖的新证据。一次改动可先过受影响的组件，再复跑整题，聚焦用例复用现有 `serial_p02`。分支交付时可带局部回执用于缩小根排查范围，跨组件约束和根入口由根检查负责。
3. **对通过的候选做一次干净副本复验。** 从同一根工作区冻结提交候选，在临时目录复现公开启动与公开检查。仅对公开约定可生成的状态使用干净初始值，须提交的产物随候选保留。复验回执绑定源码、交付产物及公开输入的哈希。任何相关改动使回执失效，最终成功绑定到实际提交版本。沿用已有 Output Guard 和受保护文件完整性检查。所有检查共享本次 trial 的剩余时间，公开整题检查通过后进入已有自检预算。耗时计入完整 E2E，首轮失败与返修回执可逐步审计。

离线验收优先覆盖“组件分别能跑但整题失败”“旧生成物导致原目录检查通过”“根入口缺失”“合并后修改引起旧回执失效”，以及 MS23 型正确交付。每个 fixture 都应在正确修复后通过公开复验。实际试验看 **通过 P 后进入严格通过的比例、A 核心 API、B 接口和 D 产物的验收增量**，同时关注检查阶段耗时与返修轮数。公开验证补齐可复验的交付路径，隐藏组合边界的收益用最终正式评分衡量。[C/MS 公开入口映射](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/run.py#L38) · [原生分支回执接口](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/branch_test_delivery.py#L102)

## 3. 加入独立局部编辑工具

建议第一版采用单文件、精确匹配的 `edit_file`。入参为 `path`、`expected_sha256`、`old_text`、`new_text`。源码版本与原片段唯一匹配时才写入。找到零处、多处或旧版本时，返回匹配数和当前版本供模型精确修订。成功时返回前后文件哈希、修改位置和有限 diff。原生 `write_file` 与分块写入继续用于创建文件和整块替换。首版的形状借鉴 DSH 的字面量替换，Codex 的多文件补丁可在后续有相应需求时评估。[SP 现有工作区工具和注册](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L776) · [DSH edit 实现](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/edit.ts#L94)

实现时把编辑接到现有路径解析、任务可编辑清单与分支所有权检查上。锁内复核版本并原子写入，使用现有变更通知更新工作区版本及检查回执。跟踪工具是否对模型实际可见，回执是否代表真实改动。相同内容不触发重建，权限拒绝和冲突返回可诊断结果。离线覆盖版本过期、片段歧义、重复提交、两个写入者、保护文件和分支路径边界。试验中测局部操作的采用率、写入字节、编辑失败率、失败到成功复验时间和 token 消耗，再看 API acc 与 Reward。源码层的工具差异已确认，编辑效率与最终准确率需各自测量。

## 4. 建议的验收顺序与对照

1. **先通过离线验收。** 三项变更各自带独立开关。复用原始 C069 拒绝序列做调度回放，用公开 fixture 验证根检查，用临时文件验证局部编辑。冻结实际挂载源码和配置、实际工具清单、可编辑边界以及公开检查步骤和哈希。保留协议请求计数、业务修改及根检查回执，便于逐阶段定位。
2. **做一次诊断配对。** 建议用 C069、C039、MS11、C068、MS41、MS23，以新跑参考 SP 同题配对，三个变体分别只启用协议降级、根整体验证或局部编辑。每条件每题 2 次，共 48 个试次，是计划数。这里的样本是按已知失败或成功案例挑选，用来确认机制是否按预期生效。冻结题包、评分器、模型及推理档、辅助预测器、总预算、并发槽、缓存策略和 E2E 起止点，平衡任务启动顺序。先比较每个开关的证据，再冻结组合。
3. **用另一组题估计组合收益。** 建议预先按 MP、N、C、MS 每类抽 3 题，并平衡已登记难度。候选组合与参考 SP 各跑两次，共 48 个试次。挑题后固定名单，开发阶段保留这些题的 trace 供最终审计。首轮对首轮是主口径。重放如要评估，另建使用相同公开触发规则和总预算的条件。最终是否扩到 59 题取决于该轮验证结果。

主指标为**核心 API acc、严格通过率和新版 Reward**。API acc 同时报告总通过用例数除以冻结总用例数及逐题等权平均。Reward 按 `delivery-bonus-50-v1` 逐题计算，记录完整性、难度权重、登记核心检查和严格通过，分别核对进度分和严格通过加分。联同完整 E2E、父子 token 与估算成本，报告单个题位的配对结果及异常状态。诊断样本小，用逐题变化和重复一致性判断。全量估计时再采用按任务配对的不确定性区间。对已有可验证评分保留原值，整份缺失按评分规则记未知，单列覆盖率。[工作区评分规则](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [逐题计算](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)

方案依据是已有评分、原始 trace 和当前源码。阈值、样本量及改进后的增益均为待验证设计。当前优先事项是让 **C069 类协议失败仍能进入实现**，并让 **C039 和 MS11 类已合并产物尽早得到整题检查的可信反馈**。
