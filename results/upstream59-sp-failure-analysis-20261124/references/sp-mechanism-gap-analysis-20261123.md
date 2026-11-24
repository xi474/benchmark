# SemanticParallel 与高分 Harness 的机制差距

2026 年 11 月 23 日 · Upstream59 v2.1.0 · DeepSeek V4 Pro 普通模式

## 摘要

Codex、DSH 和 Nanobot 的 reward 都高于 SemanticParallel（SP）。领先主要来自更多题完成了可严格验收的交付。三套基线都能接收测试失败、修改实现并复验，本轮源码和 trace 未发现它们把隐藏 verifier 设为运行时结束条件。SP 已有相同的基本反馈能力，还实现了串行自检和分支测试回执。**差距在于把验证接入哪里、验证覆盖什么，以及失败后能否回到生成最终产物的路径。**

本批证据最强的差距有三项。**分支合并缺少实际的功能证明**，首轮 166 次和重放 29 次成功交付仅验证文件完整性。**根会话整体验证未充分覆盖交付边界**，首轮 50 题通过公开检查，只有 25 题严格通过。**前沿协议出错时，直接进入业务执行的降级路径未被证明有效**，C069 首轮经历 123 次状态报告参数拒绝而没有实现业务文件。基线独有且在本轮实际使用的工具差异是原生局部修改接口，例如 Codex 的 `apply_patch`。这个差异和性能差距的独立因果关系还未测量。

## 1. 对照范围与分差

等题 ID 对齐 59 道任务，主模型均为 DeepSeek V4 Pro 普通模式。对照查看 177 个基线工具轨迹、59 次 SP 首轮和 9 次 SP 独立重放。新版 C/MS 共 30 题另作切片。Reward 沿用冻结 `delivery-bonus-50-v1`，完整性通过时核心检查比例与严格通过指示量各占 50%，再乘冻结题目权重。核心 API 仅指 A 类转换用例。一个实现错误可以同时导致 A、B、D 失败，这些失败项不能当独立根因相加。[逐题评分及 trace](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json) · [严格通过差距审计](evidence/strict-trace-audit.json) · [评分实现](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)

- **SP 首轮**为 **78.469237/138**，严格通过 **25/59**。**SP 含重放**为 **85.361619/138**，严格通过 **28/59**。
- **Codex** 为 **97.306571/138**，严格通过 **38/59**。相对 SP 首轮领先 **18.837334** 分，严格加分差 **14.5**。相对重放策略领先 **11.944952** 分，其中严格加分差 **11.0**、核心得分差 **+0.944952**。
- **DSH** 为 **91.162733/138**，严格通过 **36/59**。首轮差 **12.693496** 分，严格加分差 **12.0**。重放后差 **5.801114** 分，严格加分差 **8.5**、核心得分差 **−2.698886**。
- **Nanobot** 为 **87.535218/138**，严格通过 **32/59**。首轮差 **9.065981** 分，严格加分差 **8.5**。重放后差 **2.173599** 分，严格加分差 **5.0**、核心得分差 **−2.826401**。

从公开检查走到严格通过的比例，SP 首轮是 **25/50**，含重放是 **28/56**，Codex、DSH、Nanobot 分别为 **38/53、36/49、32/44**。这些分母各自是通过公开检查的题数。重放后，分别有 **17、18、13** 个题位由 Codex、DSH、Nanobot 严格通过而 SP 未通过。其中 SP 已通过公开检查的题数为 **15、17、12**，这些题位中 SP 的核心 API 用例都还有失分。只看新版 C/MS，SP 含重放严格通过 **11/30**，Codex、DSH、Nanobot 分别为 **15/30、15/30、17/30**。这是同题观察对照。各系统的工具和工作区执行路径、实际预算及时间不同，结果可用于定位差距，不能直接归因给某一个开关。[配对数据](evidence/strict-trace-audit.json)

### 源码与运行版本

源码对照使用本地 SP 提交 `109a65444b3d4884fe92ec9e1c543b85df34e95d`。四份归档计划记录了同一运行配置 SHA-256 `8b1a98d05f3e7eace139ccf6c4b8f7b5adbd8223426cc73c7cc475d641f79362`，自检为 `serial_p02`，**自检阶段**上限为 **300 秒**。计划挂载路径指向 `handshake_speculation_v1_report_gate_v1` 及实验覆盖文件。当前仓库该目录的 `runtime.py` 和 `tools/workspace.py` 与计划记录的**可编辑源码哈希**相符，实际挂载版本的字节哈希存在差异。下面凡涉及当时是否执行，以冻结计划和原始事件为准。源码用于核对接口和解释机制。[SP 源码入口](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/README.md) · [C/MS 冻结计划](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/experiment_plan.json)

## 2. 与基线有证据的机制差距

### 2.1 局部修改接口 · 本轮真实工具差异

Codex CLI 0.164.0 提供原生 `apply_patch`，模型可以带上下文提交局部补丁，拿回修改后的结果或失败反馈。DSH 的 `edit` 支持按原文本定向替换，默认要求单处命中。Nanobot 0.3.5 通过 `edit_file` 在已有文件上修改。按已审计的去重工具记录，本批可识别的相应调用分别为 **465、60、125** 次。SP 68 次归档的工具返回观察到 `write_file`、`write_file_chunk` 和 `shell` 等编辑入口，未观察到独立的 patch/edit 工具回执。相应的工具名字出现在 SP 的状态分类代码中，当前本机工作区工具注册里未见同名编辑工具。模型仍可通过 Shell 或生成脚本实现局部改动，两者的工具契约和反馈粒度不同。[Codex 补丁实现](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/runtimes/apply_patch.rs#L181) · [DSH edit 实现](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/edit.ts#L94) · [Nanobot EditFileTool（冻结源码指纹与行号）](nanobot-source-locations.md#edit) · [SP 工作区工具注册](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L776) · [工具审计](evidence/strict-trace-audit.json)

这项差距适用于多次定向修改同一个文件的任务。Codex 在 **C068** 写完第一版后公开检查退出码为 1，修改后通过；**MS11** 第 18 步失败，修改后第 22 步通过，随后再次生成产物并复验。基线在这些题实际用了编辑与反馈，现有数据无法拆出局部编辑接口相对 Shell 修改带来的独立 reward 增量。[逐步工具轨迹索引](evidence/strict-trace-audit.json)

### 2.2 分支合并前的功能证据 · 源码支持，归档未观察到

SP 的 `deliver_files` 核对路径与实际文件字节，记录 SHA-256。工作分支返回可信产物时，`runtime.py` 复核归属和文件内容。源码另有 `FileBranchChecks`，在声明 `required_test_targets` 或启用分支入口自检，并满足文件交付条件时，可执行对应检查、绑定版本化回执。该回执在合并前还能检查是否过期。**现有 trace 中 195 次成功交付全部为 `file_integrity_only`，`tested_targets=[]`，`tests_passed=null`。** 这说明本批可证明的合并条件停留在文件交付。是否存在未被采集的分支手工 Shell 测试，需要另查对应会话。[分支交付函数](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L715) · [运行时分支测试条件](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/runtime.py#L2339) · [版本化测试回执](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/branch_test_delivery.py#L102)

在有完整工具轨迹的代表题中，Codex、DSH、Nanobot 的根会话能在同一工作区修改组件、调用整题入口并重新生成产物。这些试次的修改与复验发生在同一工具循环内。当前证据只覆盖这条运行路径。**MS11** 中，SP 两轮各有两个交付分支，两轮均只通过 **1/10** 个 API 用例，失败项含跨组件耦合、冲突寄存器、合并和拆分。三套基线均为 **10/10**。**MS23** 中，SP 是这四套系统中唯一严格通过的系统，也有成功运用分支机制的实例。[MS11 首轮证据](https://github.com/xi474/benchmark/tree/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7) · [逐题结果](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

### 2.3 端到端执行和失败返修 · SP 已有，触发时点与验证覆盖不同

SP 已有合并后的根集成检查点。首轮 **55 题**记录到它，提示根 Agent 完成入口、打包及其余根负责产物并进行集成检查。源码的根 `finish_task` 会运行公开检查。公开检查通过后可进入串行自检，执行独立候选调用，自检通过的回执与候选源码、测试和规则版本绑定，失败可经 E1 反馈并修复。首轮 **50 题**进入串行自检，在这些题上进入时间约为各自执行时长的 **70.5%** 中位数。有 **7 题**记录自检预算耗尽，**13 题**有 E1 自检恢复请求。[根集成检查点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L816) · [根结束协议](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/output_guard.py#L481) · [自检回执与失败反馈](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_live.py#L372)

三套基线的工具循环允许模型随时调用 Shell、收到结果、编辑并复验。按识别到的显式检查命令，Codex **59/59** 题、DSH **54/59**、Nanobot **52/59** 有检查。能确认“检查失败 → 编辑 → 再检查”的分别为 **17、6、16** 题。计数只覆盖可识别的命令及失败，DSH 的部分返回只有工具已结束信息。**C039** 中 Codex 运行组件脚本、`run_all.py` 和公开检查，最终 **10/10**。SP 已有两个工作分支和根集成检查点，两轮正式 API 均为 **0/10**，没有根 `output_guard_public_check_finished` 记录。**C068** 和 **MS41** 中 SP 进入了公开检查与自检，正式 API 分别为 **8/9** 和 **5/11**。C039 体现的是交付前缺少可审计的根检查完成记录，后两题体现的是现有检查通过后的覆盖缺口。把检查提前是否能改善这些题，仍需配对消融。[Codex 工具反馈](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/stream_events_utils.rs#L348) · [DSH Bash 退出码提示](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L249) · [Nanobot 回传工具结果（冻结源码指纹与行号）](nanobot-source-locations.md#feedback)

还有一处边界差异。归档的根回调在当前工作区执行 `check.py`，C/MS 包装层由它转调 `public_check.py`，回调同时检查受保护文件的完整性。公开重放的设计使用干净副本重新判定。**未找到把干净副本的组件重建、整题公开入口和最终产物复验统一挂成每题同一根完成条件的运行证据。** 三套基线也没有通用强制关卡，优势来自有些试次主动跑了整条链。具体到 **C069**，原始 trace 显示首轮未到根自检，不能用现存产物通过自检来解释该题。[SP 公开检查回调](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L16) · [C/MS 入口适配](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/run.py#L40) · [重放设计](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-replay-mechanism-design.md)

### 2.4 控制面出错后的业务降级 · 本轮没有观察到有效闭环

SP 源码已经有重复工具熔断、E1 局部恢复、恢复预算和串行自检。首轮确实观察到 **15 题**有工具熔断、**17 题**有进展恢复请求。**C069 首轮是另一个阶段的失败。** 该题 **123 次**前沿状态报告返回参数错误，占全部首轮 **135 次**同类前沿报告拒绝中的大多数。无工作分支，末尾公开检查仍报模板 `work.py` 的 `NotImplementedError`。该 trace 未观察到把协议连续拒绝转成关闭握手、按单一路径完成根业务实现的有效降级。三套基线同题都通过根会话写实现、运行组件和公开检查，分别 **9/9**。SP 重放也 **9/9**，说明任务能完成。这个机制能解释 C069 的具体失败，样本集中度不支持把其余分差都归因于前沿协议。[SP E1 恢复](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/progress_recovery_e1.py#L644) · [C069 首轮 trace](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/trace.jsonl) · [C069 末尾检查](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/final_validation.json)

## 3. 对照结论

- **源码层面最清楚的缺口是原生局部补丁接口。** 该接口在基线实际被用来修改现有实现，SP 已有分块写入和 Shell。
- **与严格通过差距关联更强的是验证的执行位置和覆盖。** SP 已经具有分支测试回执、根集成提示、自检和恢复代码。真实运行中，195 次分支交付仍只证实文件完整性，公开检查通过后的 28 个重放策略题位仍未严格通过。根侧需要把跨组件约束、可调用入口与重生成产物一起验证，才能针对这些已观察的失败。
- **控制面降级是单题可靠性问题。** C069 有复现证据，其他问题仍需逐题区分。分块写文件、Shell 输出反馈、模型自主生成测试和失败后修复在 SP 中均有实现，本次不将这些列为能力缺失。

以上为源码和已结束 trace 的离线对照。三套基线的累积模型工作量、工具暴露和批次条件不同。没有同模型、同预算下只替换一个机制的消融，具体 reward 增幅保持未知。
