# SemanticParallel 严格通过率改进与工程实施方案

2026 年 11 月 24 日 · 面向运行时、分支调度、工具适配和评测维护者

**建议第一版交付一条可以完整演示的修错路径。** 给 SP 一个从公开规格能推导出来的小输入，让它在根工作区看到错误，定位两种实现首次分歧的地方，修改负责该规则的实现，用完全相同的输入复验，并在同一提交版本重建、通过公开整题检查。局部补丁工具解决其中的“怎样改”；能否看见错误、正确解释规则、把修复送进最终提交，分别需要其他改动。

这份报告把之前两阶段方案、PPT 第三部分、59 题逐项排错和这次工具接入核查放在同一实施顺序里。文中的**已有**指固定提交有源码，**已观察**指能定位到本次发布的试次，**建议**是拟开发或拟启用的行为。新增机制的严格通过率、时间和成本尚未重测。[59 题逐项失分和 API 差异](SP的59题逐题失分与改进报告.md) · [此前设计与实验登记草案](references/SP严格通过率改进方案-v1.md) · [历史机制分析和源码](references/Codex与DSH机制分析及SP严格通过率改进报告.md)

[证据与实施清单](#work) · [独立验证与修复](#validation) · [共享规则与业务入口](#contract) · [局部补丁接入](#tool) · [恢复、合并、交付与重放](#integration) · [基线提示与真实分工](#lessons) · [Codex 与 DSH 的反例、结束条件和重放](#counterexamples) · [离线验收、实验与指标](#rollout)

<a id="ppt-map"></a>
## 和 16 页汇报 PPT 逐页对照

第 1 页介绍研究范围。第 2–3 页给出比较起点，SP 首轮和含重放分别严格通过 25/59、28/59，DSH 和 Codex 的发布结果分别为 36/59、38/59。9 次重放追加的各题执行阶段合计为 2,703.37 秒（约 45.1 分钟），可计量 DeepSeek 费用按统一历史谷价估算增加 3.2631 美元。该时间是各试次执行时长之和。[原始比较总账](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md)

| 第 2–3 页的历史口径 | 核心 API 通过 | API 全过的题数 | 整题严格通过 | Reward / 138 |
|---|---:|---:|---:|---:|
| SP 首轮 | 633/803 | 25/59 | 25/59 | 78.469237 |
| SP 含重放，9 次中采用 6 次 | 669/803 | 28/59 | 28/59 | 85.361619 |
| DSH 发布结果 | 633/803 | 37/59 | 36/59 | 91.16 |
| Codex 发布结果 | 683/803 | 39/59 | 38/59 | 97.31 |

| PPT 页 | 讲给同学的要点 | 工程方案中的落点 |
|---|---|---|
| 4–5 · 发现错误 | Codex 在 C055 查模板间接引用；DSH 在 MS02 查两个主题争用一篇论文。公开绿后仍有可区分的业务输入 | 根首次有整题入口时封存最小输入和预期，运行真实代码，区分实现错、参考错和规格歧义。[发现与验证](#validation) |
| 6–9 · 修正与交付 | Codex 局部补丁、DSH 定位替换和读后版本检查。MS11 展示发现错序后怎样改生产代码、重跑原例、重建；C069 展示整题重放能恢复的另一类故障 | 给根和可写分支提供局部编辑，核对读到的版本；用相同失败输入验收改动，在干净候选上重建和整题回归。反复执行同一诊断而代码未变时，回到已存反例，决定修生产实现还是修正预期。[工具接入](#tool) · [合并、恢复和重放](#integration) |
| 10–11 · 分支合并 | C055 两个分支写不同文件。两个来源出现同键时应按原始位置裁决；相同别名的列号应遵循同一计算规则 | 根裁决前保留候选和位置；分支共用定位函数或同一套契约测试，分别交换输入顺序和分支完成顺序。这两个额外案例与正式失败的模板密文遮蔽分开核对。[共享规则与业务入口](#contract) |
| 12 · 业务输入 | MP19 的合法输入只删一个必填字段，归档 SP 抛 KeyError，公开约定为 ValueError | 构造单字段正反对，用真实业务入口比较返回值或异常类型。此例是公开诊断；正式失败的星号导入另有可复核输入。[案例出处](#lessons) · [逐题诊断](SP的59题逐题失分与改进报告.md#case-mp19) |
| 13 · 工具回执 | MS30 展示长文件断在中途如何续读；MP24 展示外层命令成功但内层检查失败 | 文件截断时返回候选版本与下一行，核对重复输入 tokens；每条必需检查独立留存退出码、是否执行和失败位置。[文件读取与嵌套退出码](#lessons) |
| 14–15 · reward | 实测含重放 SP 为 85.361619/138。MP19 若由 21/22 变为 22/22 且严格通过，该题由 0.954545 变为 2，增量 1.045455 | 若 MP19、MP24、MP26 各补过唯一剩余登记项，且其他结果不变，总分为 88.459742/138，严格通过为 31/59。该算术情景与正文的五题情景各自标注，实际增益须配对复测。[工作区计分规则](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) |
| 16 · 验证收益 | 两组四条件配对，分辨哪项改动起作用 | 发现与修复、分支归并与输入校验各有独立开关，条件及指标见[配对实验](#rollout)。 |

第 14–15 页按正式计分逐题折算。三题权重均为 2，若补过最后一项并达到严格通过，严格部分各增加 1 分，登记项部分各增加相应分母的一份。MP19 的 API 是 12/13，全部登记项是 21/22，两组分母用途不同。

| 三题修复情景 | 实测登记项 | 实测 reward | 达到严格通过时的条件增量 |
|---|---:|---:|---:|
| MP19 | 21/22 | 0.954545 | +1.045455 |
| MP24 | 36/37 | 0.972973 | +1.027027 |
| MP26 | 38/39 | 0.974359 | +1.025641 |

<a id="work"></a>
## 从哪项问题开始

| 59 题中已有的证据 | 决定先改什么 |
|---|---|
| 首轮 50 题公开通过，25 题严格通过。19 道失分题已完成有限自测和最终同版本公开检查。采用 9 次历史重放中的 6 次后，公开通过升至 56，严格通过升至 28；仍有 28 道公开绿、严格未过 | 先提升用例对真实规则的区分能力。保留已有公开检查和重放，并把发现错误、改对代码、交付正确版本分别度量 |
| 59 题的首轮与 9 次重放共观察到 195 次成功分支交付；回执证实文件交付完整。C055 两个分支分别解释同一条规则，MS41 的局部概率与根整合出来的联合概率不一致 | 对跨组件规则确定解释来源、分支消费接口和根的组合断言。只为有关联的产物引入联合检查，保留互不相关文件的并行 |
| C069 首轮连续 123 次同类协议拒绝。MS11 根已经看见排序错误，却迟迟未把修复写回；首轮 50 个进入自检的 SP 题，开始自检的时点中位数已到已用执行时长的 70.5% | 协议错误恢复业务工具；业务失败给可定位差异与编辑入口；根首次获得可运行候选就允许检查，保留最后的交付复验 |
| C031、C055、MP19、MP24、MP26 在采用重放的总账上各只差一个登记项，且都是 A 类 | 把真实入口、间接引用、合法边界和错误输入放在开发验收。**算术情景**：若这五题各补齐唯一失败且其他结果不变，严格从 28/59 到 33/59，reward 从 85.361619 到 90.613588（满分 138）。这不是新机制的实测增益 |
| 59 题首轮中 SP 与 DSH 的业务 API 总数都过了 633/803，严格通过却分别为 25/59 和 36/59。Codex 严格通过 38/59 | 优先看一整道题是不是从“差一项”变为“全过”、原来全过的有没有退化。API 微平均仍单列。对模型、辅助调用和重放一起计费，防止多花预算带来的收益被误归给工具 |

[逐题分母与回执](SP的59题逐题失分与改进报告.md#overview) · [首轮根检查轨迹](references/evidence/strict-outcome-paths.json) · [C069、MS11 与时点证据](references/sp-accuracy-reward-improvement-plan-20261123.md)

### 工程分工与交付件

下表的开关为建议配置名，方便实现和单独回退，现有仓库不会识别这些新名字。P0 是最早应交付、能恢复业务或建立测量的功能；P1 做到端到端闭环；P2 依据可测的瓶颈追加。

| 顺序 | 改动与负责组件 | 何时触发、交付什么 | 离线验收能看到什么 |
|---|---|---|---|
| P0 | provider、registry、运行时阶段选择；`tool_manifest_audit` | 每次模型决策生成角色、阶段、真实函数清单及摘要，关联返回的工具名、解析和执行结果 | 父普通、可写子、只读子、仅报告和串行自检的可见/可执行范围与设计逐项相符 |
| P0 | 分支握手调度；`protocol_business_fallback` | 同一代同一协议错误反复发生，保留已合并业务状态、处置待提交提议并让根回到业务执行 | 超长字段夹具只触发一次降级，后续能实际读写或检查；原错误与已付费用可追踪 |
| P0 | 工作区、registry、provider；`local_patch` | 在已有文件的小范围修改机会提供独立补丁；关联调用、补丁应用、差异及原例复验 | 能修改预期行；陈旧版本、分支越权、多文件中途失败均不会留下半份修改 |
| P1 | 调度器、根公开检查；`early_root_check` | 根第一次持有可运行整题入口时做一次非终止检查；有分支则等相关产物物化，未 fork 的任务同样可触发 | 公开失败能回根继续编辑；晚到旧回执不覆盖新候选；外部评分收到最后核验的版本 |
| P1 | D1/D2 验证器与父消息投递；`sealed_expectation` | 独立评审先从只读公开材料封存输入与预期，再执行候选，将首次差异交还根 | 正确实现、故障实现、错误参考、歧义各有不同裁决；原失败例能在修后相同入口复验 |
| P1 | 分支任务说明、接口生产者与根；`contract_join` | 多个分支解释同一规则时约定来源、次序、字段与消费者；小样例穿过真实组合路径 | 交换输入来源、别名穿过间接入口、并列或顺序变化时，都能依据公开规则判断结果 |
| P1 | 业务入口与根验证；`entry_contract_probe` | 对字段约束、短路、日期边界、副作用等选择能区分实现的小输入；经正式业务入口调用 | 记录首次失配字段以及输入或产物前后变化；探针对自身假设错误有明确回执 |
| P1 | 分支提交、根工作区；`versioned_publish` | 建立规则或文件所有权；发布时比对读到的版本，多文件改动一起提交 | 旧分支迟到、生成物过期、部分文件冲突可检出；互不相干改动保持并行 |
| P1 | 根完成流程；`clean_delivery` | 在干净候选副本重建，依次运行原失败输入、集成测试和整题公开检查，封存交付 | 仅靠上轮副产物通过的候选会暴露；重建与评分之间的提交摘要吻合 |
| P2 | Shell、文件读取、进程管理；`verified_command_receipt` | 长输出能分页取回，保留内部被测命令及最外层返回码；长验证可按句柄轮询 | 失败在日志开头、中间、子进程时都可找回；轮询同一进程，费用和时间如实计入 |
| P2 | 上下文压缩、父子回传及待办；`evidence_projection` | 保存未决差异与候选哈希，逐项识别父接收、进入父下一请求、是否据此修复 | 压缩前后原例、首差和归属仍可回读；勾完清单且缺可执行回执时显示“待验证” |
| P2 | 断点、runner 与实验总账；`versioned_recovery` | 工具/账本结清后从检查点恢复，同例复验和全新整题重放各有身份 | 中断不重复已生效写入；保留未结算请求；独立重放的触发、选用、总成本均可审计 |

P0 的观测工作与项级可靠性可并行开发；因果对照时让两臂共享基础设施修复版本。验证与修复闭环由运行时负责，正式评分器继续独立评价。默认跳过不适用的检查，例如单组件任务没有跨分支交付时就记录“不适用”，不会为凑指标再创建分支。

### 借鉴的具体出处

| 源码里确实存在的能力 | 这批基线实际观察 | SP 应保留、补齐或另行开发的部分 |
|---|---|---|
| Codex `apply_patch`、DSH `edit` 与文件观察策略 | 59 题里识别出 Codex 465 次补丁、DSH 60 次局部编辑。DSH 的 92 次写前拒绝中 91 次为未读先写、仅 1 次为读后变更；其中 88 次关联到同路径重读及成功修改 | 在原工作区提供可选独立编辑；收到陈旧回执先重读；用候选哈希扩展到分支发布。不能拿 92 次拒绝估计“避免了 92 个合并错误”。[Codex 补丁运行时](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/runtimes/apply_patch.rs#L181) · [DSH 读写校验](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/fs-observation-policy/src/index.ts#L63) |
| Codex 可续读命令和压缩长会话；DSH 可记录待办 | 5 题实际续接过 8 个进程；9 道历史 MP 有 10 次根历史替换；DSH 27 题勾完待办中只有 17 题严格通过 | 保留 SP 已有长输出回执、已有上下文压缩，按瓶颈补句柄和证据投影。清单关联可重放证据。续读与压缩只是让任务能继续，既有统计无法给它们单独分配 reward。[Codex 执行观测](references/evidence/codex-followup-evidence.json) · [DSH 清单观测](references/evidence/dsh-followup-evidence.json) |
| 两个 Harness 都能在业务工作区执行程序、读输出、编辑、复验 | DSH 在 MS02 用冲突分配例找到实现错误；Codex 在 C007 自造歧义客户后修正实现并用原例通过，最后仍未严格通过。MS41 的 DSH 差分测试还发现过参考程序自己算错 | 把“预期封存在前、真实入口对照、根收件、用原例复验”作为 SP 的具体设计。模型在一条 trace 中选了什么输入并非冻结框架的必做规则。[逐例证据与工具顺序](SP的59题逐题失分与改进报告.md#mechanisms) |

SP 自己的前沿握手降级、跨分支规则所有权、祖先候选版本保护和独立盲验证协议属于面向 SP 架构的工程设计。可以借鉴 Codex 或 DSH 如何暴露错误、如何继续工作，但不能把这些 SP 设计说成从基线中直接移植的现成功能。

<a id="validation"></a>
## SP 如何在提交前发现并修正业务错误

本章是实施建议。源码定位基于 SemanticParallel 的 `109a65444b3d4884fe92ec9e1c543b85df34e95d`。历史 59 题的正式版本、当前仓库中的可选原型和下文建议启用的功能分别登记。首轮 34 道严格未过的题中，25 道已经通过公开检查。验证的首要问题是怎样让这些题剩余的错误变得可见，并让根会话在最终提交前改对。下文的检查都只用公开材料构造，自检用例不参加正式计分。[原改进方案](references/SP严格通过率改进方案-v1.md) · [逐题数据](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

### 先复用已有实现

| 已有代码 | 可直接保留的行为 | 此次要补的接口 |
|---|---|---|
| [D1 的 inventory、snapshot_copy 和 execute_suite](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d1.py#L78) 及 [D1 私有子会话](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d1.py#L278) | 可从文件提取公开材料和函数签名，在候选私有副本执行 unittest。子会话的主工具是 submit_self_check。 | inventory 读取的是当时工作区；文档、接口签名和导入项可能已被候选改变。接入一个在 trial 开始时从原题制成的只读材料包，独立记录预期封存前验证者实际看过哪些消息、工具返回和文件。 |
| [D2 的失败修订](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d2.py#L172)、[同例重放与旧版本拦截](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d2.py#L290) | 可留存原 test ID，确认候选错误后不许修改该失败测试的方法体；更正参考时要求引用公开条款并保留原候选调用输入；相同状态可抑制重放。 | 将上述约束用于单个低成本业务场景。D2 原型本身登记最少 3 个分支、30 个用例和 600 秒窗口，整体开启会同时改变多个实验变量。 |
| [SDK 的独立候选进程](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_sdk.py#L337)、[错误反馈分类](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_sdk.py#L701)、[根会话的压缩回执](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_live.py#L294) | 能区分探针输入、子进程、断言、覆盖和时间问题，可把完整诊断存成 evidence 文件，给父历史送有限预览。 | 在回执中增加不可变 case ID、是否独立推导、候选版本、根接收回执和修复裁决。预览截断后按 ID 取原件。 |
| [根集成检查点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L815)、[根公开检查和最终版本复核](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L34) | 已对经验证的业务分支交付建立根检查点；finish 时运行真实公开检查，核对受保护文件，并在自检可完成后重跑公开检查和版本比对。 | 单独增加一种“候选首次可运行”的非终止检查回调。有子分支时在已物化的 join 后接入，无分支时在根首次建成整题入口后接入。 |

当前 `serial_p02` 可在评审阶段通过 `run_tests` 使用已有检查器，冻结配置在 C/MS 中可查到。阶段前移需要另外的回调；直接提前调用 `finish_task` 会把执行带入原完成协议并抢占收尾预算。[检查器注册与 run_tests](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L71) · [历史冻结配置](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/experiment_plan.json#L188)

### 一条反例怎样从验证者回到根

1. **冻结可见面。** 运行时从启动快照建立允许清单，包含题面、公开接口、公开示例及其出处。验证者用新会话读取这个包，其历史、摘要和工作目录与业务根分离。先封存一个有区分力的小输入和可手算期望；若使用小规模独立参考程序，同步封存其源代码、依赖、生成器种子、案例数和手算锚点。参考侧禁止导入候选。候选完整出现之前就可以准备，但首轮评估独立性时保持两臂相同启动时点。
2. **执行真实路径。** 候选侧按题面指定的入口从同一版本依次运行。先用组件函数定位，随后用实际整题入口、合并后的工作区和重建产物验证。对整合输出比对首个差异字段、数组位置或事件次序。若只测序列化后 JSON 的内容，则 Python tuple/list 的差别需要单列；若公开接口明确要求 Python 类型，则增加原生类型断言。时间、舍入、排序和容差均沿用公开契约。带随机的小规模穷举保存首个反例原始输入供回放。
3. **把证据投递给根。** 加入建议事件 `case_sealed → case_executed → root_received → case_adjudicated → case_replayed`。共用 `trial_id、branch_id、case_id、contract_hash、input_hash、expectation_hash、candidate_hash、artifact_hash`，分别记层级、时间、实际输出和期望、退出码、完整证据路径。根的下一次实际模型请求记录收到该 case ID 与首差，例如“同一 handler 内主机排序错位”。子分支报告已发、父工具已收、父下条模型请求已读三者分别统计。多分支同一反例可挂多个来源，按输入、判据和被测入口去重。
4. **裁决再改。** 将实际不一致分为生产实现错误、参考错误、输入违反前提、规格有多解和运行异常。先用最小例与原文判定方向。确认生产错误后，由拥有代码的业务分支或根修改，根重建并验证当前版本。若错在参考，单独保存新期望版本、改动原因和原回执。无法唯一判定时只检验公开能要求的不变量。断言没执行、进程超时和单纯打印“通过”分别留痕。
5. **同例闭环。** 用封存的原输入、同一入口、原期望和相同判定规则复验，比较修前和修后候选哈希。再跑受影响接口及整题公开检查。最终版本与复验版本不同时，标记回执过期，对最终提交另行回放。业务修复分子只计确认为生产错误且同例通过的事件。只有同版本正式评分才能支撑严格通过率和 reward 的变化。

### 该构造哪些有区分力的场景

| 目标 | 怎样造出可能证伪实现的输入 | 怎样确认解释成立 |
|---|---|---|
| 局部契约跨组件保持一致 | 选同一输入使两种规则解释产生不同外部结果。C055 可交叉切换可信来源、密封标签和解密键，分别观察原文保留与最终渲染。 | 在组件输出和根整合输出各保存一份差异；能指出第一次偏离的边界才定位到具体组件。 |
| 共享状态、并列与事件顺序 | 先造一个最小相关结构，再加一个不相关实体或调整声明顺序。MS41 以两个环境、两张票区分每轮共享环境与逐票独立抽取；C058 以两主机和两 handler 检验跨分支合并次序。 | 可手算时列出全部合法状态；存在多种合法解时用集合、偏序或守恒关系。Codex 的 C058 修好自建例后正式 API 仍为 1/9，所以通过一个例子只证明这一条性质。 |
| 输入规模、递归与边界 | 在同一构型中逐级扩大输入，记录最小可重现规模、错误类型、时间与内存。在很小规模用朴素枚举比对，大规模只验证题面支持的不变量和资源约束。 | 把错误答案、候选超时、参考自身超时和机器资源争用分别记账；规格未承诺复杂度时，慢本身只作为性能观察。 |
| 副作用、状态和交付文件 | 同一对象连续运行、不同对象调换顺序、失败后继续下一步，检查输入内容及可观察的状态或文件。如果题面要求事务回滚，预先封存异常后的文件清单与摘要。 | 区分“候选主动拒绝”“调用后污染下一例”和“外部评分器超时”。对有文件交付约束的题通过最终交付入口再测一次。 |
| 参考或规约存在歧义 | 写出两种解释、每种解释对应的可见依据和可区分输入。先用极小的手算锚点检验参考自身。 | 引用原条款能裁定方可修候选。DSH MS41 的自制参考本身出错；Codex C033 原断言又把 `Hi` 的 `i` 写作大写字节值。两种情形都须保留出错的原参考或断言。 |

业务形态只是选择探针的方法。具体任务编号和事后看到的正式失败只用于开发离线夹具，实际运行时由公开规格生成测试。以 task ID 硬编码预期会破坏盲验证。

### 独立消融、验收和代价

**先分开检验三件事。** ① 对独立性，两臂均只加一位评审、同一生成次数、同一检查时点和同一执行器，仅一臂在看到候选前封存期望；② 对时机，在确定的同一验证策略和候选就绪判据下，仅比较终止前检查和首次整题可运行时检查；③ 对开销，在相同验证方法与时点下比较一个手算反例和有界参考枚举。三项各自记录资源与覆盖率；若同时估计独立性与时机的交互，再做二乘二设计。调度重叠、评审人数与原任务总预算不在这些单因素比较中混改。

**断网验收。** 在父历史、实现、运行输出、摘要及非白名单路径分别埋入不同标记，检查验证者实际接收的请求和工具返回。用固定参考、一份正确候选、另一份同规约正确实现及注入确定缺陷的候选测试真阳性和误报。验证错误参考、非法输入、未执行断言、不规则排序和迟到分支结果均保留原始分类。跨分支合并过程中故意更新候选，确认过期版本不得交付回执。同一个候选、同一个未修问题不空转；根修改后必须重新构建，并能把原失败输入在最终版本上改为通过。断网验收依赖假模型回复和短小夹具，不需模型请求。[已有 D2 测试](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/tests/test_selfcheck_d2.py) · [现有自检隔离测试](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/tests/test_p02_selfcheck_isolation.py) · [反馈投影测试](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/tests/test_selfcheck_feedback_projection.py)

**性能与 reward。** 新增验证会占用父子共享 token、模型与 CPU 时间。较早启动可能隐藏部分等待，也可能撞上业务分支抢资源；应同时量取活动区间重叠、资源排队、峰值 CPU、官方评分耗时和统一外层完整 E2E。根收到确证反例后到原例复验成功的时间可直接衡量修复效率。正式结果逐题统计严格通过翻转、回退、API 命中、完整性、同版本 reward、成本和未知用量。首轮与历史重放分列。当前证据支持开展验证；新设计对总体严格通过率、完整 E2E 和净成本的影响仍待同题配对测量。

<a id="contract"></a>
## 把跨分支业务规则和非法输入验收到真实入口

本节回答三个工程问题：两个分支实现同一条业务语义时谁负责；业务层的拒绝规则怎样穿过真实入口；一个验证命令显示成功时，根怎么知道关键断言真的运行了。案例来自 59 题的冻结候选。下面的改动均为设计建议，本次只离线检查了旧结果与旧代码。

### 四道题的正式结果和对照边界

| 任务 | SP 核心通过数 | 唯一正式失败项 | Codex | DSH |
|---|---:|---|---:|---:|
| C055 | 8/9 | `A/sealed-tag` | 9/9 | 9/9 |
| MP19 | 12/13 | `api/scanner/invalid-business-field` | 13/13 | 13/13 |
| MP24 | 25/26 | `api/eu/invalid-business-field` | 26/26 | 20/26 |
| MP26 | 25/26 | `api/calendar/invalid-business-field` | 26/26 | 25/26 |

四行的 SP 首轮数值与按公开检查选用重放的最终矩阵相同。不能据此断言每题都重新执行过。MP24、MP26 上 DSH 也漏掉了 SP 的那条 API 检查。因此，Codex 在这组任务的结果适合做行为参照，成熟 Harness 自动保证所有非法输入都被验证的说法缺少依据。[冻结逐题矩阵](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

### 1. C055 的两条分支交付不同文件，根统一裁决

公开题面把可信源解析、不可信源解析分给两个 `work.py`，整合由根目录的 `integration.py` 完成。两个分支都要理解“别名中值的原来源”，可以并行处理不同文件。题面规定后声明覆盖，别名保存声明时的值位置，标签开启时密文的消费值为 `[sealed]`。归档实现暴露出三个可独立区分的问题。[题面及组件约定](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/workspace/TASK.md)

| 层级 | 在冻结候选上的离线事实 | 设计与验收 |
|---|---|---|
| 同键候选裁决 | 根把 left 再把 right 写入同一字典，随后才比较源序号。新造输入先给不可信源 `a: early`、后给可信源 `a: late`，返回 `early`；反转来源类型时能返回 `late`。 | 两组件保持公开输出形状，各保留本组按源顺序的胜者。根对于同键至少保留左右两个候选至裁决，或遍历时用同一显式优先级即时比较。测试跨来源两种顺序、同源重复和只有一个来源。若公开规定存在并列，再另测并列规则。无需引入完整历史缓存。 |
| 锚点位置规则 | 对相同文本 `a: &n one` 换行 `b: *n`，别名的值位置在可信源是列 4，不可信源是列 7。题面两类都取值首字符 `&` 的 1 起列号，此处均应为 4。 | 由一个实现负责人封存位置算法或一个两边都执行的解析契约。若允许新增共享文件，可提供同一个纯函数计算值首列和别名快照；两个组件继续各写本文件。共同测试只改变可信标记，比较值位置不变量，并允许公开规定确会改变的可信标记不同。 |
| 密文的直接读取、模板递归和导出 | 正式失败是可信模板内期望 `value-[sealed]`、得到 `value-T`。新造 `a: !vault ID`、`b: text-${a}`、`tags=true` 也得到直接读 `[sealed]`、间接读 `text-ID`。根展示条目时屏蔽密文，但递归渲染路径返回原 ID。 | 根整合组件负责“消费值”解析，直接读取和模板递归用同一入口。导出另持有原文，按题意保留 cipher ID 或模板。交叉验证直接/间接、标签开/关、解密键有/无，以及 `dump` 中原文保留。 |

只有最后一行可以映射到正式 `A/sealed-tag`；前两行是依据公开规则构造并在冻结实现上实际执行的额外反例。它们增加理解，不增加正式失分数。覆盖问题见 `integration.py` 第 12–25 行，密文渲染分叉见第 53–64、85–91 行；可信解析器第 26、55、58 行，不可信解析器第 23、32、40 行。以上用例不应作为后续正式评测提示下发。[冻结整合代码](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/workspace/integration.py) · [正式输出首差](evidence/C-probes.json)

**接入位置。** 根分解任务时，遇到两个组件共用覆盖次序、字段来源或渲染规则，可在 `BranchContext.render` 的已有分支上下文附上公开条款、字段定义、负责人及版本；分支在同一约定下交付。根收齐交付并进入 `_v2_activate_root_integration_checkpoint` 时，用能区分两种解释的小输入验证跨组件接口。在业务允许时，把同一规则集中为纯函数；固定组件对外接口和现有文件所有权。把这些动作做成可选实验开关，另计输入 tokens、验证耗时和重复实现减少量。[分支上下文](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/branch_context.py) · [根集成检查点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py)

### 2. 从明确的公开条款生成单字段变体，穿过正常业务入口

三道 MP 在干净目录执行随包 `check.py` 都返回 0；通过冻结候选的模块业务入口调用相应输入时，本应抛出 `ValueError`，三者却都返回了正常业务值。各题的合法输入形状和具体违规字段不同。这种结果可以通过比较接近的两个输入来诊断，无须窥探正式用例。[逐项离线探针与回执](evidence/MP-diagnostic-probes.json) · [公开条款和实现行号](evidence/MP.json)

| 题目 | 原因与狭义边界 | 离线验收的输入和判据 |
|---|---|---|
| MP19 扫描器 | 合法源码有普通导入，但公开条款禁止星号导入。现有 `ast.ImportFrom` 分支会接受星号，正规化成对包的依赖。 | 以同一文件树、同一入口和顶层对象分别传 `from pkg import a` 与 `from pkg import *`。前者应返回正确依赖，后者应在业务入口抛出指定异常。不能对包含乘号或星号的任意文本一概拒绝。 |
| MP24 EU 资格 | 应校验教授引用的每个部门 ID。代码遇到前一个合格 EU 部门就提前结束，排在后面的未知部门漏检。 | 把唯一非法引用分别放在合格部门之前和之后，两种次序都应抛出异常。全合法列表仍按资格筛选。不能将“不是 EU 部门”误归为“部门不存在”。 |
| MP26 晚餐日程 | 一般活动可以跨日。公开规则只限制 19:00 开始且 `kind=dinner` 的事件在当天 20:00 及以前结束，现有实现只检查结束在开始以后，仍把跨日旧晚餐收入有效索引。 | 同一晚餐分别在当天 20:00、20:01、次日 20:00 结束，依次应接收、拒绝、拒绝。最后将同一跨日事件改为 `other` 应接收，防止修复误伤合法活动。 |

**怎么放进 SP。** 公开契约提取器记录 `入口、真实函数签名、适用字段/前提、单处变异、预期返回或异常、依据`。先在独立参考侧封存期望，再从候选副本调用实际业务入口，沿用真实 wrapper 和输入装配，另保存组件与整题入口的观测。本来属于合法值域的输入保留正对照，防止靠“拒绝所有输入”得到好看的负例结果。公共规则确未定义的边界标为未裁决，避免自行扩展契约。仅当组件声明特定禁值、引用关系、早退出或条件性时间范围时生成对应检查。SP D1 的 `execute_suite`、D2 的失败归类和同例回放可复用；新增的是从业务条款映射到可执行入口及最小正反对的逻辑。记录实际执行到的入口、调用原始返回/异常、结束状态和最终候选摘要。[候选副本执行](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d1.py) · [自检与同例回放设计](#validation)

### 3. 大输出、嵌套命令和业务断言的可信回执

长输出存放、分段读取、绝对截止、跨题访问隔离及后台进程回收沿用[集成方案第 5 项](#integration)。另要解决退出码传播。当前 SP shell 的 `tools/shell.py:194` 根据直接子进程的 `returncode` 判断命令是否成功，`:203` 构造输出回执。若运行的脚本依次执行多个步骤，只依据最后一步的状态，有可能让后续成功的打印或收尾遮住前面的业务断言失败。这是通用可验证风险；上述四道题没有证据把其正式失分归因于退出码被遮蔽。[shell 实现](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py)

建议只对系统生成的验收脚本使用结构化步骤清单。让执行器分别获得子校验进程的退出码，关联同一候选、业务案例和断言；规定必须的任一步失败、超时、未执行或回执缺失均不能关闭该检查。路径允许的原始 shell 命令仍可用于调试。离线验收用三例：关键子进程返回 7 后外层正常打印并返回 0；校验进程被超时中断但清理成功；关键错误位于长日志中段且只阅读了末页。第一例应保留内部失败，第二例应记超时，第三例应可按偏移取回原文。均不得仅据外层 0 或末页文字判定业务检查通过。

### 如何检验对严格通过率和 reward 的预计影响

以上诊断已观察到的是旧实现如何失败及相应值差，没有测到这些改进部署后的收益。先用公开材料生成此前未使用的测试，离线检查能否揭示旧问题且保留合法输入；再以相同模型、预算和任务做独立配对，报告公开来源反例命中、修后同例通过、干净整题检查、最终严格通过、注册核心 API 分子/分母、耗时和成本。正式 reward 按 `delivery-bonus-50-v1` 逐题复算，严格部分仅在该题全部严格条件满足时计入。通过单一开发反例只支持那条性质；未正式重评分时不能把预期增量写为实测。

### 如何从逐题修法抽出可以复用的运行时检查

研发可按下表选离线验收夹具。每一题的候选预期、差异字段、代码位置和可执行的修法都在逐题报告。算法层面的建议交给解题 Agent 按该题当次公开规格推导，运行时只提供检查方法和证据传输。

| 可复用办法 | 来自哪些失败 | 如何在 SP 上实施 |
|---|---|---|
| 用小规模参考解检查全局耦合、最优解、并列和见证 | C011、C039、MS02、MS11、MS14、MS28、MS30、MS41、MS42 | 封存手算例或小规模可穷举的两个可行解，分别投影成组件结果和最终结果；区分遗漏可行解、排序方向、全局状态共享、规模导致的超时和参考自身不正确 |
| 把事件顺序与最终值同时验收 | C033、C049、C058、C062、C066、C068、C074、C077 | 在公共规则指定的事件节点记录短序列；试同一时间发生、迟到回调、取消、重复提交、类型改变等变形，比较首个状态分歧。程序输出和资源使用分列 |
| 功能模块保持自己的入口，根验证一次真实交接 | C055、MP01、MP02、MP06、MP15、MP20、MP21、N17 | 分支交付字段定义、责任与版本；根用一个能区分两种类型/顺序/解释的小输入穿过上下游。对生成的查询、文本或程序，用独立消费者真实读取或执行 |
| 同时断言成功、应拒绝、允许的副作用和调用方数据 | MP07、MP19、MP24、MP26、N24 | 记录公开条款、输入变动、预期的返回/异常、调用前后摘要和第二次调用结果，测试正反二例。业务入口收到了什么要可见 |
| 用与题面一致的执行环境核验输入输出边界 | C031 | 使用真实终端、等待和输入语义，区分驱动器环境不支持和候选输出有误。无法在本机复现的观察留为静态判断，保留冻结回执 |
| 独立检查业务是否实际推进、产物能否全新生成 | 已恢复的 C069、MP14、MP25，以及部分改善的 MP01、MP20 | 暂停后台控制面后仍能回到根实施，按依赖顺序重建。保存首轮与重放两份身份。过去的恢复能告诉我们该测什么，额外机制的净效果仍须另测 |

[逐题修法与回归](SP的59题逐题失分与改进报告.md#unresolved) · [重放恢复的三题](SP的59题逐题失分与改进报告.md#recovered)

<a id="tool"></a>
## SP 的局部补丁工具是否真正提供给了模型

2026-11-24。核查范围为 SemanticParallel 已发布源码和 Upstream59 的 59 份首轮、9 份重放 trace。只读查询 GitHub 得到唯一远端分支 `main`，提交为 `109a65444b3d4884fe92ec9e1c543b85df34e95d`，与本次核查的 [已冻结的 SP 源码](https://github.com/xi474/SemanticParallel/tree/109a65444b3d4884fe92ec9e1c543b85df34e95d) 一致。若同事已在另一个工作副本、容器镜像或 MCP 服务接入补丁工具，本次没有取得那份版本和对应的新 trace。

### 59 题中的实际清单

按每次 `model_request` 对应的 `fork_only_parent_passthrough` 或 `fork_only_child_envelope` 的 `tool_names` 统计。首轮与重放各自的清单总数均与模型请求事件数一致。计数单位为 Agent 决策轮。原始网络日志 `wire_requests.jsonl` 只保存工具数等摘要，无法单凭它还原逐项名称。

| 批次 | 父普通清单 | 父特殊清单 | 子清单 | 合计清单 | 含独立 apply_patch 或 edit_file 的清单 |
|---|---:|---:|---:|---:|---:|
| 59 题首轮 | 1,941 | 712 | 1,294 | 3,947 | 0 |
| 9 题重放 | 358 | 108 | 240 | 706 | 0 |

首轮返回记录中有 817 次 `write_file`、34 次 `write_file_chunk` 和 1,819 次 `shell`。这些数包含失败返回，shell 也用于阅读和测试。以上证据支持的结论是，历史运行中模型没有机会选择同名的独立补丁工具。要判断接入后的模型是否试图调用，必须使用接入后版本的原始清单和回应。

两个批次各自的清单去重后都是 13 种工具，均未出现含 `patch` 或 `edit` 的名称，模型生成的函数调用同样为零。逐条检查模型生成的 `shell.command` 也未发现独立词 `apply_patch`。这个检索不能排除通过 Python、sed 或脚本间接修改文件。

C055 的 [trace.jsonl](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl) 可以直接复核。第 8 行列出父普通首轮工具，第 59 行只提供 `report_frontier_state`，第 368 行并列子会话的可见工具与允许执行工具，第 1111 行进入串行自检，第 1115 行列出自检的文件、shell 和收尾工具。这四种决策时机都没有独立补丁工具。trace 路径清单见 [semserve-trace-metrics.json](references/evidence/semserve-trace-metrics.json) 的 `initial`、`retries`。

### 发布源码中的接入路径

下列路径相对于 [SP 运行时目录](https://github.com/xi474/SemanticParallel/tree/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo)。

| 问题 | 源码可确认的行为 |
|---|---|
| 工具是否注册 | `tools/workspace.py:776` 的工厂列出工作区工具，没有 `apply_patch`。`cli.py:675` 把 shell 和工厂产物交给 registry，`--mcp-only` 会跳过这组原生工具；`cli.py:683` 可以额外连接 MCP。`tools/registry.py:62` 从已注册实例生成 schema，`tools/registry.py:197` 遇到未知名称返回 `UnknownToolError`。 |
| 名称是否一致 | 若通过 MCP 接入，`mcp/client.py:305`、`mcp/client.py:314` 将本地名称组装为 `mcp__<server>__<tool>`，归一化并截到 64 字符。提示和计数都须使用发出去的真实名称；只查裸名会漏掉 MCP 调用。 |
| 是否真的会收发补丁 | `providers/openai_compat.py:62` 默认 `tool_choice=auto`，`:101` 写入 `payload["tools"]`，`:392` 解析回应中的 `message.tool_calls[].function` 并对 `arguments` 作 JSON 解码。若使用这个 provider，可注册一个标准 function，定义必填字符串参数 `input`，将解码后的精确多行字符串交给补丁实现。只把补丁写法放进提示，或模型仅在普通文本里给出 diff，都不会经过这条函数路由。 |
| 根、分支、自检能否使用 | `runtime.py:4619` 按状态选取 schema；已有待处理 offer 时可只发决策函数；修复轮只发指定工具；前沿报告轮可只发报告函数。`fork_only_prefix.py:15` 对普通父清单做快照；`:42` 比较常规工具集合，`:48` 在子清单中分别记录可见名、可执行名。`runtime.py:4812` 和 `output_guard.py:296` 在串行自检限制并行控制工具，同时保留局部修复路径。 |
| 为什么 grep 到名字仍不够 | `runtime.py:2376` 在工具成功后用包含 `edit_file/apply_patch` 的集合识别产物写入。这一处不会创建工具、生成 schema 或执行补丁。`write_preflight.py:16`、`:33`、`:98` 有针对现有写工具的检查；接入新写工具时必须验证等价的工作区、分支所有权、并发和写入后状态保障。 |

### 新接入版本的离线验收与观察

1. 固定实际启动的 commit、容器镜像摘要、入口、MCP 配置和 provider。用临时目录里的现有文件作为输入，沿正式入口构造父普通轮、可写分支轮、串行自检轮、仅报告轮。前三类按设计验收是否允许局部修复，后一类保留原协议约束。将 registry 名称与实际发给 provider 的函数名、JSON 参数类型和 tool_choice 逐项对齐。
2. 使用本地模拟 provider 返回一次合法 JSON 函数调用。核验响应解码、路由接受、文件发生预期的局部修改及测试结果。另测上下文过期、不属于该分支的文件、多文件补丁和重命名的源/目的路径，确认拒绝发生在违规写入之前。无需诊断模型请求。
3. 对之后已授权的自然运行，只记录脱敏工具名、schema 摘要、scope、轮次、tool_choice、模型原始调用名、调用被拒原因与文件差异摘要，避免采集密钥或原始敏感内容。分别计数可见、已选、成功执行、生成预期差异、用原失败输入复验通过。若模型选择了 shell 改写，也应单列。
4. 分母用“已有文件、已知需局部修改、scope 允许写、该轮同时可选补丁工具”的轮次与题数。首次建文件、只读探索和仅报告轮单列。只有在有修改机会且实际暴露的轮次里仍未调用，才能进一步检验工具说明、模型偏好和整文件写入替代策略。能调用与能提高严格通过率，还需不同的证据。

### 工具接口按哪一种格式接

本项目的 Codex 复现走过“Responses 自定义工具 → Chat 函数 → Responses”这条桥。冻结桥接器对自定义工具要求 `arguments` 只有一个字符串键 `input`；收到被输出上限截断的工具调用则丢弃未完整的调用。SP 原生 OpenAI-compatible provider 读取 Chat `message.tool_calls`。建议在 SP 注册**一个标准函数**，共用 `input` 作为唯一外部参数，内部把已解码字符串交给补丁解析器；去掉 Responses 专用封装。保持日志内的真实注册名与外发名一致。[Codex 冻结桥接器](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/reproduction/gateway/codex_tool_response.py#L40) · [SP provider 的请求与回应](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/providers/openai_compat.py#L101)

```json
{
  "type": "function",
  "function": {
    "name": "apply_patch",
    "description": "对已经读取的工作区文件应用局部补丁。上下文过期时重新读取文件再编辑。",
    "parameters": {
      "type": "object",
      "properties": { "input": { "type": "string", "description": "完整的多行补丁文本" } },
      "required": ["input"],
      "additionalProperties": false
    }
  }
}
```

工具实现只处理补丁语法、当前角色可写的工作区路径及候选基线。使用与原 CLI 相同的一套语法夹具，涵盖增删行、上下文不足、找不到唯一位置、多文件以及重命名。拒绝绝对路径、越过作用域的源或目标、符号链接解析后越界和版本过期。每个变更先在私有候选上完整解析并比对，然后在持有目标锁或单一发布引用时提交，跨文件按同一版本发布；剩余文件失败时工作区仍保持原候选。成功回执提供真实变更路径、前后内容摘要及简短 diff，失败提供类别、重读路径与定位信息。直接 Shell 写若仍允许，靠隔离工作副本及发布检查保证相同的版本约束。

| 新版本中发现的第一处断点 | 应检查的部位和修法 |
|---|---|
| 工厂有实例，最终父/子业务请求无该函数 | 比对实际镜像、启动入口、MCP 前缀、角色权限、父前缀缓存生成时机与阶段过滤。仅在按设计可编辑的轮恢复工具，核验最终传输的 schema/摘要与离线构造一致 |
| 请求含函数，模型仅输出代码块或自然语言 | 查实际响应有无结构化 `tool_calls`，核对 `tool_choice`、函数描述和参数例子；在有真实小改机会的轮比较整文件写、Shell 和补丁的选择。脚本化强制调用只检验接线 |
| 返回函数调用，分发失败或没有文件差异 | 比较 wire 名、解析的 `input`、实际调用名和回执；覆盖 CRLF、中文、转义换行、分块传输和截断。勿把字符串二次 JSON 解码或把文本中看似补丁的字段当成成功 |
| 有真实差异，正式失败仍存在 | 对照补丁改到哪个文件、哪个入口和哪个候选版本；原输入是否从失败变为通过、根有没有重新构建、评分实际拿到哪份产物。修复成功率和工具采用率各设分母 |

同事新版本只需提供本次启动的 commit 或镜像、第一条**确有修改机会**的脱敏请求工具清单及相应工具回执，就能定位上述第一处断点。未来测试“提示模型优先局部改”时，以工具已经真实暴露为入组前提。保留创建新文件、生成所需产物以及确需整文件重写的原有入口，避免把强制使用工具造成的耗时算成方法本身的开销。

<a id="integration"></a>
## 让一次局部修复可以可靠地交付给整题

SP 已能按分支声明写入文件、校验交付、在根执行公开检查，并在部分模式下对最终版本复验。59 题归档中有 166 次首轮、29 次重放的成功分支交付，195 次回执证明文件完整性。当前缺口是根如何证明这些文件相互配合、在重新生成产物后仍符合相同的公开规则。以下七项均为待实现或待扩展的设计。所列行号固定到 SP 提交 `109a6544`；某能力存在于源码、在具体历史试次实际启用、能够提高严格通过率，三件事分别核实。[SP 机制与原生 trace 清点](references/sp-mechanism-gap-analysis-20261123.md)

### 1. 协议连续拒绝后，恢复同一根会话的业务执行

**现有证据。** C069 首轮前两代前沿报告成功，第 3 代连续 123 次因为 `done_add.0` 长度超限被拒。根最终触及 128 步上限，未开始实现，核心 API 为 0/9；独立重放为 9/9。E1 已会记录自检差错并基于检查和相关变化提供纠正反馈。握手阶段另有专用工具选择及未提交的投机预测，需要在握手分支自行处理反复拒绝。建议分别接到 `_v2_after_tools`、`_v2_schedule_frontier_handshake`、`_hs_discard`，把实际恢复动作和现有 E1 账目对齐。[C069 原件及两次结果](references/sp-accuracy-reward-improvement-plan-20261123.md#source-line-13) · [握手后的工具回执](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L685) · [握手调度](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L121) · [丢弃投机票据](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/handshake_speculation.py#L244) · [E1 反馈](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/progress_recovery_e1.py#L644)

**实现和验收。** 按任务、握手代、字段、约束类型累计。首次错误返回字段、实测长度、允许长度及一例合法最小结构。可试验“同一签名两次或同代累计三次”阈值；不同合法报告清零。到限后记录失败原文与原因、撤销本次未消费的并行提议和投机票据；让同一根从已验证文件及剩余总预算继续，禁止旧异步结果稍后重新提交。已启动子任务依其既有交付规则安全排空。回放 C069 旧报文并注入轮换字段、一次过长后正常提交、有合并分支时迟到的票据；断言下一轮实际可读写、有一次真实业务动作、最终检查仍会拒绝错误候选。降级能节省协议空转和 tokens；过早触发会失去本可利用的并行，需同时报告降级率、首次业务动作延迟及严格通过率。

### 2. 用共享的业务规则解释分支结果，再做跨组件语义合并

**现有证据。** `BranchContext.render` 已把目标、读入引用、依赖、验证器和交付路径给子分支；`_v2_activate_root_integration_checkpoint` 在验证文件交付后将根转入整合。MP06 的两处实现都按字典理解快照，局部逻辑可以彼此自洽，但正式接口期望列表。C055 要跨位置处理密文标记；有明确的规则归属可避免两个分支各用一套解释。把这些案例用作离线开发诊断，不向未来被测 Agent 注入历史评分器的未公开断言。[已归档 MP06 诊断及逐项证据](evidence/MP.json) · [分支上下文](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/branch_context.py#L36) · [根集成节点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L815)

**实现和验收。** 在创建相互依赖的分支时，为共用规则生成一个有公开出处、版本和负责人的契约，列输入形状、输出形状、非法值、排序或副作用。生产方、消费方和根均引用相同版本。分支交付携带一条实际调用、输入、预期和输出，区分“已产出”和“已验证”。根使用真实两个组件串接一个从公开规格派生的小样例。冲突时保留双方证据，根回到原文裁决；公开原文确有两解则标歧义，避免在运行时凭猜测强加隐藏要求。验收包括“生产者返回字典而消费者需要列表”和“两个文件一致采用同一个错误解释”：后者只有与公开条款独立导出的预期才能发现，双方表决无效。契约编写和联调增加 tokens、调用及根的串行时长，优先在有实际共享字段/状态的连接处启用。

### 3. 跨文件的同一规则指定负责人，修改已有文件必须带读取版本

**现有证据。** `reconcile_delivery_ownership` 及 `_assert_concurrent_file_ownership` 已检查并行分支的具体文件归属；`write_chunk` 也顺序检查分块偏移。但一个业务决策可能同时落到多个文件，整文件覆盖也可能基于过期读取。两个分支分别实现同一规则并不等于它们改写同一个文件，C055 应检查语义归属和调用链，再判断是否真的出现写冲突。[现有文件所有权](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/delivery_ownership.py#L25) · [并行所有权检查](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/planning.py#L661) · [整文件与分块写入](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L151)

**实现和验收。** 对共享规则指定唯一发布者，其他分支通过显式接口消费，保留不同文件并行。根或分支持已有文件读取得到的摘要提交局部修改，写入端在同一临界区比较原摘要、检查补丁唯一命中并原子替换文件。涉及一组必须一致的文件时，整组暂存、统一比对前置版本与规则版本后一次发布。旧版本只返回受影响路径和变更摘要，让调用方重读、重算；拒绝部分提交。跨 Shell 的业务写入也必须经过隔离快照及发布时比对，否则工具层版本检查可被普通脚本绕过。离线同时编辑相同文件、相同大小不同内容、跨文件发布中途失败，以及互不相关的写入；验证前三种能保护新版本、后一种仍并行。代价是哈希、暂存、合并和可能的返工；记录陈旧提交次数及被阻塞的关键路径时间。

### 4. 在同一个干净交付副本上完成重建、公开整题检查和封存

**现有证据。** `make_public_checker.check` 在当前候选执行 `python3 check.py`、检查受保护文件，完成前再次执行公开入口并核对工作区版本；D1 有 `snapshot_copy` 和 `execute_suite`。MP14 首轮根 trace 中下游报告曾先于帧产物运行，独立重放已严格通过。以该题说明顺序和陈旧副产物风险；它不能证明所有失败都来自产物污染。[根公开检查](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L34) · [候选复制与执行](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d1.py#L98) · [MP14 原始诊断](evidence/MP.json)

**实现和验收。** 根的交付阶段从登记的原题材料及该版本的实现封出干净副本，排除上次运行的生成物和测试缓存，保留原始输入与锁定依赖。按公开入口或已声明的生产者→消费者依赖先构建；在**同一副本**执行跨组件最小用例、公开整题和必要的原失败用例，用源码、依赖、入口、构建命令及应提交产物摘要共同标记候选。评分器所接收的交付物必须与被核验的对象一致，或按已登记的交付方式核对重建摘要。源在运行中变化，回执失效；依赖缺失、超时、公开失败分别回报，禁止复用旧绿灯。对故意残留正确旧 JSON、倒置两个生成步骤、中途修改同名入口、公共检查会正常写缓存四个场景做验收。干净构建会增加磁盘和 E2E；控制为每个候选版本至多一次，低成本组件检查可先反馈。

### 5. 长验证命令用受管句柄续读，足够长的输出按需取回

**现有证据。** `ShellTool.execute_with_context` 轮询任务专属进程，遵守取消及自检截止时间。长输出已可由 `_output_receipt` 保存到工作区外层逻辑排除的运行时检查目录，返回末尾、相对路径和哈希。建议在正式挂载版本核对实际回执，再补长命令的跨调用续读。[执行及截止](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py#L48) · [输出回执与受管清理](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py#L203)

**实现和验收。** 仅对允许的无交互公开验证/构建返回任务域内的句柄，关联候选版本、绝对截止、进程组以及起始时间。支持按字节偏移、最大字节数读 stdout/stderr、看最终退出码、取消属于本任务的进程组；同一命令及候选复用活跃句柄。输出原件留在同任务受限存储，工具返回经权限过滤的分片和摘要。普通业务文件索引排除日志。任务结束、取消、超额或候选变化时清理进程；活跃/已终结未知、输出落盘失败都单列，不把模型“看到日志”当作命令成功。验收用首行有关键错误的大日志、60 秒构建期间轮询、派生进程继承管道、假造另一题句柄和预算到期。收益可能来自避免重复启动及反复回填长输出，代价是磁盘、后台并发资源和剩余验证等待时间，需对照整题 E2E 与实际 CPU 秒。

### 6. 上下文压缩时保留可核验业务证据，检查根是否实际收到

**现有证据。** `_tool_evidence` 已提取退出码、路径、摘要、错误和有限输出；`compact_messages` 生成压缩后的消息。`BranchContext` 也明确区分继承的父证据与子自己执行的动作。已有这些能力，尚需验证结构化差异是否完整跨过“子交付→摘要→父下一次实际模型输入”三个边界。[工具证据投影](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/context_compaction.py#L72) · [压缩入口](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/context_compaction.py#L156) · [父子上下文说明](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/branch_context.py#L36)

**实现和验收。** 为新发现的失败保存“候选版本、公开条款、用例引用、独立预期、实际输出、退出码、负责方、复验状态”；详细原件通过内容哈希在本任务内按需取回。压缩时先保留尚未裁决的差异和已确认回归，成功的重复流水用摘要。子交付时登记证据 ID，根的工具回执和下一次实际模型输入分别记录 ID 与投影摘要，又一次修改后以新 ID 回报。真实上下文窗口不足时保留显式“未传递”状态，避免将模型叙述推断为父已接收或使用。用长输出中段唯一失败、两份异版本同名证据、压缩前后各一次交接验证；核对父读到了哪条差异，并在预算内可用原输入复现。索引和短回执也占上下文，可比较压缩后输入量、关键差异召回率及父重复调研次数。

### 7. 分开设计进程断点恢复、同题内复验、独立整题重放

**现有证据。** CLI 有 `load_trace_checkpoint`，根能从完整工具历史恢复已物化文件的集成阶段；D2 有候选套件的 `replay_group`。历史另设了“干净公开检查失败后独立重做整题”的资格和选用规则，实际 9 次重放，6 次采用，严格通过数从 25/59 变为 28/59。这是已执行策略的净变化；不能据此预估新断点设计或在公开已绿的题上做重放会得到相同增益。[CLI 恢复](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/cli.py#L172) · [根阶段恢复](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L882) · [候选测试套件复验](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d2.py#L290) · [登记的整题重放规则](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/semserve/20261121-replay-mechanism-design.md)

**实现和验收。** 在分支发布、根完成一次公开验证、失败用例已复现时原子写断点，包含配置、当前候选内容地址、根和子会话、已提交工具调用、证据、计量账本及在途请求。中断后先对根候选和已发布版本对账；已完成的副作用按唯一 ID 跳过。请求已发但没有结算凭据时保留未知，结算前隔离该 attempt 与其预算；无安全断点时只允许从已验证版本继续并登记差异。原失败用例在新版本复验属于同一 attempt；独立重放另建身份。预登记可见触发条件、次数和总预算，并记录首轮、重放单独结果、是否采用以及两次总成本，禁止按隐藏分数事后挑高分。分别模拟“文件刚发布就断电”“请求发出后丢响应”“公开已绿但最终未严格通过”“重放仍失败”。验收应观察到不重复副作用、未知仍为未知、无资格不触发、失败原件保留。断点会增加快照、存储和对账成本；重放还有整次模型费用及 E2E，单独列每新增一题严格通过消耗的已结算金额和时间。

**落地次序。** 先把上述失败和正常对照固化为公开或合成的断网验收。优先接入握手原地恢复、候选版本保护和干净交付，再用小规模可独立切换的分支契约/根联合验证测量语义效果；后台命令和证据投影待确认瓶颈后分开评估。记录各阶段是否实际触发、每题首轮和策略采用后严格通过、登记核心通过率、独立 API 通过率、完整 E2E、父子合计 tokens、已结算成本和未知用量。缺失正式评分时保留未知。上述工程补丁对 reward 的影响均须同预算配对重测；本节未实施改动或发起模型试次。

<a id="lessons"></a>
## 从原生提示、逐题轨迹到 SP 的可验证改动

这一节补充三类容易混淆的证据。源码能证明工具或提示存在，轨迹能证明这一次实际怎样用，正式评分用于判断最终分数。给 SP 的设计仍须配对实验测量。旧 PPT 核对的是含 16 页、第三部分为第 10–15 页的版本，文件 SHA-256 为 `287e192e9f0b92cabebe5517046db77b55670332e0c943b5648604d55479bdf6`。[16 页配套 PPT](slides/sp-codex-dsh-strict-pass.pptx) · [旧版行为分析](references/Codex与DSH如何发现并修复错误——SP严格通过率分析.md)

### 1. DSH 的通用自检提示和 MS02 的实际时机

下列原文分别来自实验启动消息和 DSH 原生系统提示。审计在 59 个归档根会话都找到了三段文字。[59 题自检逐项审计数据](evidence/dsh-postpublic/audit.json) · [全库审计](DSH公开检查后的59题自测审计.md#source-line-21)

| 来源 | 归档提示原文或原文片段 | 生效范围 |
|---|---|---|
| 任务启动包装层 | “Complete the task in the current /app workspace and run relevant checks.” | 对所有任务提出相关检查要求。 |
| DSH Agent Team 系统提示 | “coordinate them explicitly and have the Lead review the final diff and run tests.” | 上文的 them 指 Bash、格式化器、代码生成器和脚本，提醒 Lead 协调这些操作并检查最终差异。[固定源码第 39 行](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/experimental/tool-agent-team/src/index.ts#L39) |
| DSH Bash 工具系统提示 | “Check the [exit code: N] marker on every bash result; investigate failures before moving on.” | 每次 Bash 返回都可据退出码识别失败，是否新造业务输入仍由模型决定。[固定源码第 254 行](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L254) |

Codex 的基线提示也有普适原则，要求从改动附近的针对性检查逐步扩大覆盖。它在 C055 选择了模板嵌套密文这一输入；源码没有给它预置该场景。[Codex 固定源码第 153 行](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/protocol/src/prompts/base_instructions/default.md#L153)

MS02 规定“每主题必须选一篇，不得重用论文”，无完整分配时返回 null。题面还给出公开检查命令，没有要求构造特定反例。原始 `agent/dsh-stream.jsonl` 第 80 行公开检查通过；第 88 行模型提出试空主题和无解；89–90 行 Bash 跑了“一篇论文争两个主题”，真实入口出现解包 None 的 TypeError。94 行用 edit 修改 integration.py，98–99 行复跑同一输入返回 None。103、108 行继续构造其他输入，131 行重跑公开检查，138 行给出 final。整条根会话没有调用 finish_task，提出反例发生在原生最终答复前，未观察到当时有框架额外插入“现在举反例”的消息。DSH 该题正式 API 9/9 并严格通过。SP 在同题失去的是平局与并行证据两项，这个成功修复不能解释两套系统在每一项上的差距。[题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS02/instruction.md) · [DSH 原始 ZIP](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip) · [两条可核验的修复](DSH公开检查后的59题自测审计.md#source-line-16)

**给 SP 的单独提示消融。** 可在现有公开检查首次通过、还有业务预算且当前候选未收到过该提醒时，在下一个根业务轮只加一句提示：“从公开规格挑两条会共同限制输出的规则。若能写出区分两种实现的小输入，执行前先写预期，再通过整题入口运行，记录实际差异。若规格不足，请指出缺哪项依据。”此句为本报告拟稿。两臂固定模型、预算、工具、时点、收尾和重放策略，仅切换提示；单独记录是否实际送入模型、是否执行新的业务输入、是否首次揭示了生产错误、同例复验和正式评分。扩展模型本人的提示与新增独立盲验证者是两个因素。前者实施简单，有可能增加模型调用和无效自测，也可能只增加文字叙述。DSH 的 45/59 题已有公开检查过后主动业务自测，33/45 在最终严格通过，不能用这个事后比例推算新提示的提升。[全库计数与判断边界](SP的59题逐题失分与改进报告.md#mechanisms)

### 2. C055 两分支写哪份文件，错发生在哪里

题面把可信和外部文档解析分别分给两个组件。SP trace 第 331、332 行登记了不同的 branch ID、work.py 和 result.json；第 944 行由 root 调用 write_file 写入 integration.py。这里有三个实现责任，未见两个业务分支争写同一个文件。[交付合同与根写入记录](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl#L331) · [题目列出的两个独占产物](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/C055/instruction.md)

三个具体输入与正式失分的对应关系见[共享规则与业务入口](#contract)。

### 3. 旧第三部分还应保留的具体改动

| 建议 | 基线证据及局限 | 最小离线验收和实际代价 |
|---|---|---|
| 对要求拒绝非法值的接口采用一对相邻输入 | PPT 第 12 页 MP19 只删除合法样例的 `entry`，SP 得 KeyError，Codex 得题面约定的 ValueError。Codex 的通用提示鼓励针对性检查，此题逐个校验字段是当次产物选择。此公开探针不能证明它恰好命中隐藏输入。 | 输入 A 合法且成功，输入 B 只改变一个字段，记录错误**类型、位置、候选版本**。按公开形状生成，范围疑义记为待判。容易添加，但负向输入过多会挤占功能测试预算。[冻结比较与原文](references/Codex与DSH机制分析及SP严格通过率改进报告.md) |
| 文件截断后直接给出续读位置 | PPT 第 13 页中 DSH read 支持起始行和行数，MS30 的 4 次调用实际只传文件路径；SP 当次多次改变最长读取长度，最终用 sed。受管长命令和文件读取游标是两个接口。 | 在 SP read_text 回执中兼容增加读取范围、文件版本和 next_line，跨页遇版本变化时提示重读。用相同长文件检验拼接无缺行、已经读过的前缀不重复，并观察读到目标处的总 token 与时间。当前源码的 `truncated` 表示内容是否截断。[DSH 读工具](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/read.ts#L82) · [SP 读工具](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L54) |
| 每条必需检查单列退出码 | PPT 第 13 页 MP24 中，外层运行返回 0，但输出里有导入错误和内层 exit:1，Codex 读输出后修导入、重跑三种检查。尚无证据表明其框架自动识别该嵌套故障。SP Shell 的默认回执也取外层子进程 returncode。 | 要求运行器逐条记录检查身份、命令、候选版本、退出码、实际执行状态；上游失败造成后续未执行要单列。离线构造先失败、最后一条成功的命令组，汇总必须保留原失败。额外成本主要是回执长度与分步启动开销。[SP Shell 退出与输出](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py#L190) |
| 把跨分支义务保留到下一业务轮 | DSH 有可跨轮替换与投影的 todo_write，33/59 题使用，27 题最终勾完，其中 10 题仍未严格通过。 | 在业务清单上区分声明完成和已有同版本运行凭据，以未满足的交付义务安排下一步。限制清单长度；记录遗漏数、净 token、误勾以及清单维护与实际业务的时间占比。[源码和分层统计](references/sp-codex-dsh-reward-tradeoffs-20261123.md#source-line-56) |

旧 PPT 的第 14–15 页是条件测算：MP19、MP24、MP26 若各补最后一个登记项、全部转为严格通过且其余成绩不变，含重放总 reward 从实测 85.361619 升至约 88.459742。增量约 3.098123 是可检查的算术情景；尚无 SP 改版的正式评分可把其中任何增量归给定位共享、字段检查、提示、续读或退出码采集。[冻结逐题指标](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json) · [工作区计分政策](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json)

<a id="counterexamples"></a>
## Codex 与 DSH 怎样构造反例，何时停止，怎样重放

### 两条 Codex 轨迹给出的直接证据

**Codex 与 DSH 都能在公开检查通过后，主动构造公开样例以外的业务输入，运行候选并据此修正实现。** 在这些实例中，根 Agent 读取公开规则后自行选择输入，通用命令工具执行程序。下面两道 Codex 题足以确认这种能力存在；其 59 题的发生频率还需同口径的全量标注。

| Codex 题目 | 额外输入如何暴露错误 | 修改、复验与最终结果 |
|---|---|---|
| C007 客户实体识别 | 第 22 步公开检查通过。第 31 步用 `exec_command` 执行 `stress5.py`，两位客户共享家庭资料，另有一条无法唯一归属的记录。脚本退出码为 0，但打印的三个预期单例与实际两个分组不同 | 第 32 步用 shell 改写 `integration.py`，第 33 步复验同一脚本得到三个单例。同一步里的另一个场景仍有分组差异，最终正式 API 为 3/8。[C007 原始轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C007.zip) |
| C058 多主机通知 | 第 19 步公开检查通过。第 23 步用 `exec_command` 向两台主机安排不同通知，从打印的事件序列中识别出处理器的主机次序错误 | 第 24 步用 `apply_patch` 修改排序逻辑，第 25 步用 `exec_command` 重跑同一输入。该序列顺序得到修正，最终正式 API 为 1/9。[C058 原始轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C058.zip) |

这给 SP 的验证回执提出了一个具体要求。应同时保存命令退出码、输入、预期和实际业务输出。C007 的进程已经正常执行；只有比较两份分组，才能看见要修的错误。

### DSH 每题补测多少个场景

以一次试次中**首次观察到整题公开检查通过**为起点，按实际执行的不同业务场景去重。原输入复验一次仍计同一个场景，同一参数枚举或随机生成套件计一种。299 是场景数，其中包括第一次就通过的输入。现有证据无法给出“每题真正发现了几个缺陷”的均值。[59 题场景索引](DSH自造场景逐题索引.md)

| 统计分母 | 观测结果 |
|---|---|
| 能定位公开检查通过时点的 53 题 | 299 个新业务场景，平均 **5.64 个/题** |
| 其中实际执行过新业务场景的 45 题 | 平均 **6.64 个/题**，中位数 5，范围 1–26；最终严格通过 33/45 |
| 全部 59 个登记题位 | 每题平均 **5.07 个已确认场景**；另 6 题缺少解题期间公开检查通过的可比时点 |
| 有证据表明新例首次暴露实现错误、改代码后同一输入通过 | **2 题，MS02 和 MP15**，两题最终都严格通过 |

53 题中另有 5 题只复核已有公开输入或产物，严格通过 2/5；3 题只为通用读取接口造例，严格通过 1/3。各组由实际行为事后划分，不能用组间通过率之差估算自造业务用例的因果收益。[59 题行为分类及严格结果](DSH公开检查后的59题自测审计.md)

**DSH 没有“反例全部通过即结束”的判定。** 冻结版运行循环中，一次正常模型响应没有后续工具调用时可返回 `completed`，达到输出上限则另记 `max-tokens`。MS02 第 98–99 行原失败输入已经通过，第 103、108 行仍继续测试其他场景，第 131 行再跑公开检查，第 138 行才给出最终回复。运行时结束与外部评分器判定整题严格通过是两个独立事件。[DSH 运行循环](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/core/agent-loop/src/agent.ts#L547) · [MS02 原始轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip)

### 怎样测试允许模型运行自造输入的收益

若研究**提示能否抑制主动补测**，只将验证提示改成“只运行已有公开检查”，保留原工具，用轨迹核对是否仍执行了新输入。若研究**执行自造输入、看到反馈本身的收益**，两组使用同一受控运行器、编辑能力、公开检查、构建入口和预算，只让实验组额外提交自造业务输入并接收结果。根、子 Agent 和后台进程沿用本组的执行策略；通用 shell、解释器和可传任意参数的业务入口都要纳入范围。记录额外调用的输入摘要、是否实际执行及结果是否进入下一次模型请求。

只移除 `apply_patch`、`edit`、`pytest` 或子 Agent 不能实现这一消融，C007 仅用 shell 就完成了造例、修改和复验。只在一组移除整个 shell 又会同时损失普通调试与构建能力。上述实验可控制**外部执行和反馈**；模型在内部是否设想过反例无法由工具日志判定。

### “重放”分别指什么

| 口径 | 本批证据 |
|---|---|
| 同一次试次内用原输入复验 | Codex 的 C007、C058 和 DSH 的 MS02、MP15 都有直接观测。复验消耗归入原试次。 |
| 用已有上下文恢复会话 | 冻结 Codex CLI 支持 `resume`，冻结 DSH CLI 的 TUI 模式支持 `--resume <id>`。这是源码能力，是否实际使用要查对应试次。[Codex CLI](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/exec/src/cli.rs#L174) · [DSH CLI](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/apps/cli/README.md#L28) |
| 公开检查失败后，在新环境用新 Agent 从头做整题 | 本次 59 题只有 SP 登记了这套统一的重放及采分规则，9 次重放、6 次采用新成绩，9 次均计入代价。Codex、DSH 的同例复验、会话恢复及运维修复分别记账。[SP 重放规则与证据](SP的59题逐题失分与改进报告.md#replays) |

<a id="rollout"></a>
## 上线顺序、实验与验收

### 第一个可交付版本先闭合哪条链

1. **冻结当前入口。** 固定源码、镜像、题包、父子实际工具、摘要/预测模型、当前完成协议、每题共享预算和 trace 格式。用合成的两文件公开小题模拟“根已通过公开例，间接入口仍处理错一个值”，另备一份正确实现和一份等价但实现不同的正确版本作为阴性对照。
2. **先暴露，再改对。** 第一次得到整题入口时检查。验证者读公开规约并封存有区分力的期望；根收到同一输入的实际差异后能打开对应实现、局部修改、重建、执行同一原例、最后提交刚验证的版本。在合成任务中演示失败转通过的全过程，并人工核对谁看到过候选、谁修改了文件。
3. **注入三类故障。** 一类是业务分歧，例如模板间接引用或共享状态的计算顺序；一类是集成故障，例如旧分支覆盖新文件、旧产物依然正确；一类是运行故障，例如协议连续被拒、子进程报错外层仍返回零。每类另有同构正确对照。记录系统是修了生产、修了参考、降级继续，还是保留未解。隐藏正式检查与答案只用于报告后的离线核对。
4. **可选能力分别打开。** 清单、后台句柄、证据压缩、扩大的独立检查、整题重放均单独配置。在两臂共用的基础设施上做同题对照，同时改了多个位置的整包只能回答“整包有没有用”。观察不到真实阻断的功能留到瓶颈出现时验证。单纯重复同一个绿样例不会给出新的业务覆盖。
5. **保护默认和故障数据。** 未通过离线夹具的版本不进入效能比较；模型正常运行但业务做错计入结果；基础设施中断、无分、未知用量、参考错误和重放单列。关闭各开关后，用录制的固定响应回放，确认工具权限、分支调度和原有公开验收恢复基线语义。

### 减少重复验证和上下文开销

DSH 的 `todo_write` 提供跨轮清单。在这批 DSH 试次中，33 题调用过它，其中 27 题最终把清单全部勾完，仍有 10 题未严格通过。SP 可复用已有分支状态，用一份**短的验收事项清单**关联 `requirement_id、owner、candidate_hash、evidence_id、status`。由模型标记“已做”，由运行时依据同版本可执行回执标记“已验证”；状态进度和证据通过分别展示。只跟踪跨组件或交付必要项，以免每次请求重复回填长清单。验收夹具包括“全项被手动勾选但原例仍错”“改产物后旧回执失效”“压缩后只取回遗漏的一项”。[DSH 的实际清单使用](references/evidence/dsh-followup-evidence.json)

按 `candidate_hash + 入口 + 输入/期望摘要 + 环境` 缓存确定性检查，保存原件；有时间、随机或外部状态的检查要保存种子或明确标为不可复用。根修了生产文件后，失效受影响的回执，并在最终版本上重跑必要整题检查。验证分支超过预算、同一候选无变化又重复同一断言，回传已有证据与未解决约束。衡量去重命中的同时统计误复用率、完整 E2E、缓存未命中输入 token 和额外评审费用。

### 收益要用什么实验衡量

PPT 第 16 页的两组四条件配对可分别登记。第一组设**原版、只加强发现、只加强修复、两者同时加强**，比较已知缺陷检出率、参考误报率，以及同一失败输入在修改生产代码后转为通过的比例。第二组设**原版、只改分支归并、只加业务输入校验、两者同时改**，在冻结的留出任务上比较严格通过与正式 reward。第一组里仅加强修复时，由基线原有检查发现错误并走新修复路径；没有发现错误的题仍计入整题结果。两组均固定模型、总预算、并发与重放规则，分别报告首轮和含重放的净增、回退、完整 E2E、tokens 与费用。两组均是拟做的对照。

**离线接线验收**可用脚本化 provider、合成公开题和归档候选完成。**自然选择与正式 reward**需要随后登记的同模型、同预算、相同题包与评分版本的配对运行。使用过的 59 题已经过事后分析，适合定位和回归；验证普适性还需冻结未用于开发的题，或另取新任务。历史 24 次诊断、48 次冻结验证是已有登记草案，开关配置与现有指标先对齐，再决定是否实施。[原配对和分层方案](references/SP严格通过率改进方案-v1.md)

| 要回答的问题 | 对照与分母 | 主要结果及代价 |
|---|---|---|
| 独立验证能不能更早暴露真实错误？ | 相同席位、预算、时点和执行器，仅改变生成预期前可见的材料。早检查与晚检查在另一组只改变时点 | 发现真实缺陷题/适用题、参考误报、发现时剩余时间、附加模型和 CPU 用量 |
| 局部补丁能不能提高改对的概率？ | 同一已暴露错误、相同上下文和编辑权限；对照保留现有编辑通道，处理组另提供可选补丁 | 有真实编辑机会时的选择率；首次改对率；同一输入修后通过率；已有正确行为回归；输出 tokens、冲突及回读次数 |
| 共用规则与入口验证分别贡献多少？ | 用二乘二设计分别打开“规则来源与根合并检查”和“正常/边界/失效业务输入验证” | 两项的主效应和交互，按题聚类。报告本来已严格通过的题有没有回退、并行等待及集成时间 |
| 协议、版本和交付可靠性是否改善？ | 同一录制输入或成对自然运行，分别注入握手错误、并发冲突或过期产物，另有正常对照 | 从第一次协议错误到下一项成功业务动作耗时、在当前会话恢复率、最终候选与评分工件一致率；重试费用和中止数 |
| 整包能否提高业务指标？ | 同题同重复的基线与改进 SP。相同模型和推理档、并发、CPU、工具权限、父子总预算、重放及采分规则；冻结两臂实现后再评 | 主报首轮严格通过的新增/回退/持平/无分，再报采用重放后的结果、业务 API 的微平均和按题宏平均、正式 reward、完整 E2E、tokens 与成本 |

逐题用 [workspace_reward.py](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py) 和 `delivery-bonus-50-v1` 重算，保留版本、难度、完整性、严格、登记项通过数及冻结分母。API 单列 A。完整性通过时，reward 等于难度权重乘以（0.5 × 登记项通过率 + 0.5 × 严格通过标志）；完整性明确失败为零，缺正式回执或换算依据保留未知。严格通过并非“自检全部通过”。新增效益按处理臂减基线，另列涉及的原始题号与配对。按任务汇总不确定性，禁止将 803 个相关检查当成 803 个独立试次。[工作区政策](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [逐题计分代码](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)

完整 E2E 从统一外层 runner 接收该试次到最终评分及收尾结束；队列外等待另报，并拆出准备、业务、根集成、自检、正式评分、清理，以及父子重叠和资源等待。记录输入/输出、缓存命中/未命中、所有父子和辅助模型请求的已结算估算额及未知笔数。基线缺完整外层时钟的历史执行时间只和同边界比较。另报每净增一题严格通过的增量费用和时间；净增小于等于零时不计算这一比值。公开已绿的剩余缺口、额外验证引入的回归及时间尾部三者必须同时展示。

**给实现同学的首个验收演示：** 从一条根收到的真实业务差异出发，点开原输入和预期，再看到对哪个实际文件作了什么改动、复验的是哪个相同实例、最后评分用的版本。能做到这一步，团队才有条件比较“多发现了错误”“修成了已知错误”和“整题严格通过增加了多少”这三个不同结果。
