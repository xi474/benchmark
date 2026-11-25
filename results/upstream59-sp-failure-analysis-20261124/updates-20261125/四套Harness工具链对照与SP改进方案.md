# 四套 Harness 的工具链，以及 SP 应优先补哪一环

2026 年 11 月 25 日 · Upstream59 同题对照 · DeepSeek V4 Pro 普通模式

本篇汇总使用 11 月 20–21 日 SP 旧基线。11 月 25 日复测的 29/59 严格通过、87.687758/138 reward 及更新后的配对，见[复测逐题摘要](https://github.com/xi474/benchmark/blob/4fe8cbfa807ba6dda55d836ed5361046c1fdbdb7/results/upstream59-full-retest-v31-20261125/analysis/%E5%85%A8%E9%87%8F59%E9%A2%98benchmark%E5%A4%8D%E6%B5%8B%E6%8A%A5%E5%91%8A-20261125.md)和[Nanobot 独立报告](Nanobot工具链分析与SP改进建议.md)。同事现已公布[运行时工具清单追踪和写入条件门](https://github.com/xi474/benchmark/blob/4fe8cbfa807ba6dda55d836ed5361046c1fdbdb7/results/upstream59-full-retest-v31-20261125/runtime-patches/README.md)，本文有关新增入口的建议需以该部署为基线测量。

开发接手可直接读 [SP 严格通过率改进实施手册](SP严格通过率改进实施手册-20261125.md)。手册按合并顺序给出代码接入点、父子回执格式、错误处置、断网验收及配对方案。

四套系统指我们的 SemanticParallel（历史归档名 SemServe，下文称 SP）、Codex CLI、DeepSeek Harness Agent Team（DSH）和 Nanobot。工程问题是：拿到一个只差几项检查的候选实现后，模型能否定位差异、修对代码、复验，并让最后提交的文件保留这次修复？

**建议先把 SP 分支测试的结果送到父 Agent 手里，再改进局部编辑的使用体验。** SP 已经有搜索、写文件、运行命令、自检、分支隔离和文件交付。缺口出现在步骤之间。旧首轮 166 份成功的文件交付回执都只验证了文件完整性。父 Agent 可以收到文件、哈希和子任务的文字总结，但从这些回执还无法确认哪条业务检查在这版文件上跑过、是否用到了真实接口。Nanobot 最值得借的是便于模型使用的单文件精确替换；Codex 和 DSH 则提供了从明确错误恢复编辑、复验原输入的实例。三者均未在这 59 题原生运行中实际创建子 Agent。SP 在 55 题观察到跨分支模型请求重叠，值得保留这项能力，优先改善分支合并后的正确性。[历史交付回执分析](references/tool-evidence.md#receipts) · [首轮与重放总账](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md)

## 一、四套系统在同一组题上做到了什么

| 系统与取数方式 | 核心 API 转换用例 | 严格通过 | 工作区 reward / 138 |
|---|---:|---:|---:|
| SP 首轮 | 633/803 | 25/59 | 78.469237 |
| SP 使用原定重放策略后 | 669/803 | 28/59 | 85.361619 |
| Codex CLI | 683/803 | 38/59 | 97.306571 |
| DSH Agent Team | 633/803 | 36/59 | 91.162733 |
| Nanobot | 647/803 | 32/59 | 87.535218 |

SP 首轮与 DSH 的 API 通过数同为 633，严格通过却差 11 题。SP 应用既定重放后，API 比 Nanobot 多过 22 项，严格通过仍少 4 题。逐题看，两者均严格通过 19 题、仅 Nanobot 通过 13 题、仅 SP 通过 9 题、两者均未过 18 题。因此可以用同题成功轨迹查找遗漏的条件，也要保留 SP 原本做对的题检查回归。单看 API 总数无法说明差异集中在哪些题，更无法给某个工具分配因果贡献。[逐题冻结评分](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json) · [Nanobot 逐题核对](evidence/nanobot-tool-audit-59.json)

分数直接汇总自每题已登记的 `delivery-bonus-50-v1`。每题为完整性因子 × 发布时冻结的难度权重 ×（0.5 × 严格通过 + 0.5 × 已过登记核心检查数 / 冻结核心检查总数）。表中 API 只含 A 组转换用例，reward 的进度分覆盖 A/B/D/P，另有严格项。SP 的 9 次重放中 6 题采用新成绩；其他三套取正式矩阵选中的试次。下文 SP 的工具次数只统计首轮。今天做的是离线核查，表内沿用原评分。[评分政策](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [工作区计算实现](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)

## 二、按功能对照整条工具链

表中“未见入口”限定在实验时的模型可见清单。shell 可以承担多种角色；工具可见、模型选择、工具成功返回、正式评分通过分别取证。

| 在一次真实任务里要做什么 | Codex CLI | DSH Agent Team | Nanobot | SP 在实验中的对应能力与差距 |
|---|---|---|---|---|
| 列文件、定位符号与上下文 | `exec_command` 跑 cat、sed、rg 等，59 题都有 cat 命令 | `read/glob/grep` 加 `bash`；56 题 Bash 命令出现 find 或 grep，专用两项调用为 0 | `list_dir/find_files/grep/read_file`。搜索可带上下文，读取可从特定行继续 | **已有同类能力**。`list_files/read_file/search_text/shell`。59 题都调用了读取；专用搜索当轮均未被选用。原生读接口按字符截前缀，搜索能回路径和行号。长文件错误处的就近阅读可以改进 |
| 新建、重写或分块输出文件 | 用补丁新增、更新和删除，也能在 shell 中生成文件 | `write`；已有文件受读状态检查 | `write_file`；本批另由适配器加 `write_file_chunk` | **已有**。`write_file/write_file_chunk`，写入遵守分支归属。48 题有同一作用域再次写同一路径并改变内容。SP 已能纠错，整文件改写会增加输出 |
| 做一个小改动或跨文件改动 | `apply_patch`，能返回具体路径、上下文或补丁格式问题 | `edit` 精确替换，同时检查文件是否读过或已改变 | `edit_file` 单文件旧文→新文；结构化 `apply_patch` 处理多文件，可预检 | **旧批缺独立局部编辑入口**。同事另有已接入补丁的版本，其实际清单、调用率和逐题结果待核实。可把单文件替换接到同一个补丁执行器，复用权限与版本检查 |
| 读取失败原因并恢复编辑 | 465 次 patch，451 成功、14 被拒。上下文不符时可以重读并改写补丁 | 91 次写入遭先读检查拒绝，87 次随后读同路径并成功写入或编辑 | 返回改动的路径、行数；文本找不到或多处匹配时有定位反馈 | **部分具备**。已有结构化拒绝、所有权及哈希。可按“版本过期／多处匹配／非本分支路径”给出不同后续动作和最小上下文 |
| 运行实现、构建、测试，取回输出 | `exec_command/write_stdin`，可沿已有进程会话继续读；代码和检查可在同一工作目录连续执行 | `bash/job_output/job_list/job_kill`；回显可含真实非零退出码 | `exec` 返回输出、stderr、退出信息；有 `exec_session`，本批未用 | **已有执行器**。SP `shell` 返回退出码，可保留长输出；分支有私有镜像和 G1 测试入口。外层管道成功可能掩盖 Python 失败，私有测试的创建、运行与报错恢复也可简化 |
| 组织步骤、选择分工 | 菜单含目标和协作工具；3 次 `update_plan` 在本桥接环境均未获支持 | `todo_write` 用了 88 次；另有目标、团队任务、workflow | 有目标及会话工具；按任务选择是否调用 | **已有自己的实现**。`report_frontier_state/choose_execution_mode_v2` 支持判断串并行。任务清单有助执行，但本批不足以支持单独引入 todo 会提高 reward |
| 派工、分支工作、回传 | 协作菜单支持 spawn、等待、消息；59 份拓扑均仅根会话 | `spawn_teammate/send_message/wait_agent` 等；46 题查询 Agent 列表，59 题均只有根 | `spawn/send_session_message/read_session` 等；59 题无 spawn | **SP 有实用优势**。分支拥有独立工作区、交付路径和合并协议。55 题有实际工作的分支；直接 `spawn_subtasks` 仅 4 次，因为选择执行模式也会触发分工 |
| 同一 Agent 同时查多个文件 | 25 题同一步提出多个调用，完整执行区间缺失，实际时间重叠未知 | 56 题有原生调用至返回区间正重叠，口径包含在途等待 | 17 题的 19 个批次有实际工具区间重叠，均为找文件或列目录 | **已有只读工具批处理**。分别统计同一模型步的多调用、实际工具时间重叠、跨 Agent 模型请求重叠。三种指标不能互换，也不能直接折算节省的 E2E |
| 检查候选、结束、再次尝试 | 可执行自造样例并重跑原输入，结束时检查待处理消息等；有会话恢复源码 | 可用读、改、bash 重跑原例；会话可写检查点 | 实测在同一工作区编辑后重跑；工具返回、模型诊断、下一次命令可逐条对应 | **已有自检、结束和选定重放**。`finish_task` 与可见检查并存；旧批 166 份成功交付仅证明文件完整。最欠缺的是向父会话交付与当前文件绑定的业务测试结果，以及根合并后跨组件实测 |

联网搜索、图像、消息、目标管理等工具也计入完整清单。DSH 有网页和读图工具，Codex 有读图工具，Nanobot 有网页和消息工具；Nanobot 的唯一一次 `web_search` 失败。本批是本地实现题，未发现增设这些外围工具与严格通过的直接联系。全量数据按四系统、每题、每工具保存了“何时可见”和“实际调用次数”。[全工具清单和 236 个系统×题记录](evidence/four-toolchains-59.json) · [工具计数的取数方式](references/tool-evidence.md#tools)

**如果按“要不要给 SP 新增工具”来决策，可以划三档。**

| 判定 | 实际功能 | 工程决定 |
|---|---|---|
| 已有，可直接复用 | 文件枚举、文本读取与搜索、整文件和分块写、shell、受控分支并行、文件交付、公开检查失败后的既定重放 | 保留 SP 的工作区所有权、读写调度与现有执行器，直接在其上扩展 |
| 有底层能力，模型得到的信息不足 | 指定行段读取、搜索命中邻域、编辑拒绝后的定位、分支私有业务测试、父会话对交付版本的验证、合并后整题复验 | 优先补模型能看懂的输入、失败返回和版本关联；核对这些内容真的进入下一轮请求 |
| 历史模型清单未见等价独立入口 | 单文件精确替换及多文件补丁；像 `write_stdin/exec_session/job_output` 的运行中命令句柄；独立图片读取或网页搜索 | 补丁先对齐同事版本。长进程管理仅在证实命令被迫重复启动时引入；当前业务失败证据不足以支持优先加图片或联网工具 |

## 三、最值得借哪些设计

### Nanobot：让模型用很小的代价改对一个已知位置

**单文件精确替换优先于再造一套多文件补丁。** 59 题中 `edit_file` 125 次、覆盖 26 题，`apply_patch` 4 次、覆盖 3 题，两项去重合计 27 题。129 次均有编辑成功回执，包含对测试辅助文件的编辑。Nanobot 的多文件补丁说明甚至写着它是代码编辑的默认工具，而模型更常选择小替换入口。这个现象支持给已有补丁后端提供更易选用的接口；只有联合实际改动、复验和评分才能判断它对 SP 的收益。[Nanobot 文件工具源码（安装包定位与指纹）](references/nanobot-source.md#filesystem) · [结构化补丁源码（安装包定位与指纹）](references/nanobot-source.md#apply_patch) · [逐题使用数据](evidence/nanobot-tool-audit-59.json)

- **如何定位。** `read_file` 用了 1,511 次，显式指定行段仅 7 次。在 MP16 中，模型先读同一实现第 100 行附近，再往前读第 88 行附近，随后做精确替换。这是分页读能帮到的具体场景。建议给 SP 的搜索命中附带上下文、行范围和文件版本，点对点续读。若要抑制重复读取，只在内容未变且原结果仍在当前模型上下文时省略正文。[MP16 轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MP16.zip) · [搜索源码（安装包定位与指纹）](references/nanobot-source.md#search) · [读状态缓存（安装包定位与指纹）](references/nanobot-source.md#file_state)
- **如何确认改的是哪一处。** 单文件接口接收旧文本和新文本，支持期望匹配数、指定第几处或行提示。建议 SP 默认只提交唯一匹配，歧义时给出候选行供重读；回执带改动路径、前后版本和增删行数。多文件补丁可先整批预检再应用。本批 4 次多文件补丁均未使用预览，因此预览的使用收益仍待测。[编辑与匹配源码（安装包定位与指纹）](references/nanobot-source.md#filesystem)
- **怎样把错误真的改掉。** N17 第一次跑 `python3 run_all.py` 外层返回 0，但依赖列表异常为空。模型缩小到带前导空格的表达式，看到 `ast.parse` 报错，给解析输入加了 `.strip()`，再跑原命令得到正确依赖，最终 A 为 9/9、严格通过。框架提供读、改、执行及回显。识别“空依赖不合理”、选择这条输入是当次模型行为。[N17 原生轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/N17.zip)
- **哪些收益容易高估。** MP03 从缺少最终报告到补入生成步骤，重跑原检查通过，正式 A 为 21/21、严格通过；MP02 修了索引路径，同一组件复验也通过，但正式 A 仅 14/16。Nanobot 的 1,072 次 `exec` 中，877 次工具正常返回，其中 88 次命令退出非零；另 195 次为工具失败。应分别记录执行器状态、被检查程序状态和独立正式结果。[MP03 原件](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MP03.zip) · [MP02 原件](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MP02.zip) · [调用与返回配对](evidence/nanobot-tool-audit-59.json)
- **暂缓移植的工具。** 本批没有用 Nanobot 的持久命令会话或子 Agent；已观察的实际工具重叠只涉及文件发现。分块写由实验适配器提供，SP 自己已有。它们对某些任务有用，当前没有证据把它们排在严格通过问题之前。[实验适配器（实验适配器定位与指纹）](references/nanobot-source.md#nanobot_observed_runner) · [只读批处理源码（安装包定位与指纹）](references/nanobot-source.md#execution)

### DSH 和 Codex：让错误可见，也让被拒绝的编辑有下一步

DSH 的读前置约束有实际恢复证据。41 题共 91 次写入因未先读取而被拒，87 次随后在同路径出现成功读取并再次改写。可借的是把“当前文件版本与所见版本不一致”变成能直接操作的提示；SP 可以把提示附在已有作用域拒绝与补丁回执上。DSH 在 C033 也遇到 `... | head` 掩盖断言失败，模型从输出发现问题，对比实际和预期寄存器，修改后重跑。最终 A 为 14/14。DSH 的 bash 提供输出和退出信息，辨认那条断言是这道题的行为。[DSH 文件工具](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/error.ts) · [Bash 源码](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L254) · [C033 轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C033.zip)

Codex 在 MP24 的第 34 步看到外层退出 0，但输出有 `ModuleNotFoundError` 和内层 `exit:1`。第 35 步同一补丁修了 4 个组件的导入，第 36 步复验三种入口，之后又换工作目录运行整题，正式 A 为 26/26、严格通过。另在 MP02 和 MP15，它都从一次“同一补丁对同一路径重复操作”的拒绝恢复，改好补丁后都跑了公开检查；最终只有 MP02 严格通过。对 SP 应分别记录“编辑针对的是哪一处”“同例已绿”“合并后的整题也绿”。[MP24 轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MP24.zip) · [Codex 补丁诊断与 MP15 对照](evidence/codex-tool-diagnostics-20261125.json) · [补丁上下文匹配源码](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/apply-patch/src/file_update.rs#L156)

这三套基线的根 Agent 都能用执行工具构造新输入、比较预期、编辑并复验。没有证据表明某个专用“反例工具”会让它们每题自动找出正确反例。Codex 轨迹恢复和 DSH 会话检查点也要与 SP 另起候选的公开失败重放分别统计。[Codex 会话恢复](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/session/rollout_reconstruction.rs#L189) · [DSH 原生轨迹审计](evidence/dsh-native-chain-59.json)

## 四、SP 的实施顺序与验收

| 优先项 | 实际改动 | 离线验收与取舍 |
|---|---|---|
| 1．一个调用完成分支私有测试，父任务能看见结果 | 复用 G1 私有镜像与现有测试执行器。给可写分支提供明确入口，将候选文件、测试和输入版本、实际执行数、首个断言差异、退出状态和完整日志位置写入结构化回执。在合并结果和父模型下一次真实请求中显示摘要 | 导入失败应显示业务检查尚未执行；算错应显示实际值与预期值；正确候选应通过。更换候选、依赖或输入须失效旧回执。分支越权仍被拒。增加测试时间与少量上下文 |
| 2．根 Agent 在合并后的文件上复验公开规则 | 对涉及多个组件或入口的修改，从两条公开规则的交点选一个有区分度的输入，先登记预期。观察失败后改实现，保留同输入复验，再运行公开整题。上游依赖未齐时标记待集成；由根任务接手 | 用一对仅在该规则上不同的离线候选，正确者绿、错误者红。在 N24 类“值正确但修改输入”题，测试子进程要能观测调用前后的参数。额外运行应报告时间、tokens 和成本 |
| 3．把已接入的补丁变成模型能选、失败后能恢复的日常工具 | 先取得同事实际 commit 和请求清单。对小修开放单文件精确替换，可作为已有后端的薄封装。基于文件版本和所有权校验，失败返回候选行，成功返回改动与版本，复用同一写入路径 | 根和可写分支分别验证可见、可调用。测唯一匹配、多处匹配、过期读取、跨作用域、部分失败，以及修复是否抵达最终文件。可能节省输出；多接口也可能增加选错成本 |
| 4．提高长文件定位效率 | 扩展现有读取、搜索参数，支持起始行、行数、上下文、下一段位置。长错误保留原始日志引用 | 修改后或压缩会话后再读必须能拿回新正文。测首次准确定位轮数、重复读取的 tokens、读错文件率。只读工具时间重叠和 API 通过率独立报告 |

第 1 项能直接落在现有代码上。SP 的 G1 已实现 `_unit_check`，分支交付结构也能携带测试目标。当前合并给模型的摘要保留 `content`、`delivery_verified`、`materialized_files`、`tested_targets` 等字段。可扩展摘要以区分“文件已交付”“私有检查通过”“真实依赖下集成检查通过”，并与交付版本绑定。历史首轮有 42 题共 64 次尝试用原生写工具创建分支私有测试而遇归属拒绝；另有 11 题的 35 条 shell 回执出现外层 0 和真实 traceback 同时存在。两类都有明确的离线回归样例。[G1 执行器](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/g1_branch_checks.py) · [父模型摘要代码](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/runtime.py) · [错误回执明细](evidence/tool-feedback-paths-59.json)

第 2 项解决另一类失分。SP 首轮最后一次有限自检通过的 37 题中，19 题正式严格未过；按原定重放选取后，42 题自检通过，21 题严格未过。C055 中，SP 分别测试钥匙和密文等情形，最终仍漏了模板引用与遮蔽规则的组合，A 为 8/9。Codex 在同一模板引用上对比三种权限情形，正式 9/9；该实现测试前已正确，因此不能把此项登记为“测试发现并修好”。已有自检的改进目标是能区分错误候选，并让分支各自成立的规则在同一个根入口同时成立。[C055 与 N24 证据、离线复现](references/tool-evidence.md#receipts)

**验证 reward 增益的最小实验。** 用同事安装了补丁的准确版本作共同基线。先只开第 1 项，再在相同条件上加入第 2 项；第 3 项独立比较现有补丁与等权限单文件入口。固定题目、模型模式、父子总预算、评分器、并发资源和重放策略。用上述已知轨迹做工程验收，另在事先冻结且未用来调规则的题上检验收益。每题公布严格通过翻转（新增和退步分别列）、A 的通过数/分母、登记核心检查、工作区 reward、tokens、成本和用时；SP 历史仅有执行阶段计时，新批若比较完整 E2E，应从启动到独立评分结束统一计时。缺记录的试次保留未知。行为指标记录父会话是否实际收到有效回执、是否用同输入复验、修复是否进入最终交付，单独列仅修改测试的情形。这样即使 reward 不升，也能定位是工具没被选、错误没暴露，还是修复在合并时丢失。

## 五、复核入口和证据边界

- 系统版本为 SP 发布提交 `109a6544`、Codex CLI `0.164.0`、DSH Agent Team `0.2.1-rc.2`、Nanobot `0.3.5`。Nanobot 59 题均有该版本的实际客户端请求快照，正式新 30 题镜像中的五个关键源码文件与所用源码存档哈希一致。旧试次仍按各自档案保留。[SP 固定源码](https://github.com/xi474/SemanticParallel/tree/109a65444b3d4884fe92ec9e1c543b85df34e95d) · [Codex 固定源码](https://github.com/horacezoe/CodexAndDSH-/tree/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe) · [DSH 固定源码](https://github.com/horacezoe/CodexAndDSH-/tree/c31818a6f5581ff86b42619a71c4fc391a84ee1f) · [Nanobot 实验源码（安装包定位与指纹）](references/nanobot-source.md)
- 四套分别读到 3,947 份 SP 模型工具清单、2,137 份 Codex 网关请求观察、1,450 份 DSH 网关请求观察、2,127 份 Nanobot 实际客户端菜单。Codex 的网关可能仅存协作命名空间，客户端展开快照可核实具体工具。DSH 有 36 份请求标为客户端省略清单。这些数量均不能视作成功工具执行数。调用频次分别取各自原生的模型工具调用记录、轨迹步骤、DSH 工具事件、Nanobot 启动事件。工具可能失败，调用次数也不直接代表效率。[四系统逐题清单](evidence/four-toolchains-59.json) · [Nanobot 调用结果](evidence/nanobot-tool-audit-59.json) · [DSH 工具/并发/会话](evidence/dsh-native-chain-59.json)
- 同事报告的“加入 patch 后 reward 提高 0.4”暂缺可和当前基线配对的逐题结果、单位与采用策略。本文将它作为有待复核的新版本观测，上述建议的增分均为待检验假设。[补丁增分的证据范围](references/tool-evidence.md#patch)

本次还用工作区计分函数逐条核验了表一的 295 行选用记录（5 行口径 × 59 题，含重复选用的历史结果），全部与冻结分数一致。Codex 的原生客户端有 2,132 份带 14 项的工具清单，另有 10 份实际空清单；118 份配置意图快照另存。逐题并发资料全部缺少完整执行区间。Nanobot 的 438 个工具批次中，逐对比较单调时钟并对照原生完成事件，确认 19 个批次共 45 对调用实际重叠，其中 31 对是两次文件查找，14 对是查找与目录枚举。这些计数支持把“工具能并行”与“这次确实并行”分开评价。[Codex 客户端与逐题拓扑](evidence/codex-menu-parallel-59.json) · [Nanobot 逐题时间区间与行段读取](evidence/nanobot-batches-59.json)

### 附录：实际模型请求出现过的工具名

下列是跨题并集。名称本身不代表某次调用成功；也不能拿名称个数比较功能多少。Codex 的命名空间按子工具展开，一次计数。DSH 的 `glob` 与 Codex 用 shell 的 `rg` 可以服务同一个检索需求。

| 系统 | 实际工具名 |
|---|---|
| SP（13） | `list_files, read_file, search_text, write_file, write_file_chunk, shell, report_frontier_state, choose_execution_mode_v2, spawn_subtasks, report_blocked, deliver_files, deliver_frontier_report, finish_task` |
| Codex CLI（展开后 14） | `exec_command, write_stdin, apply_patch, view_image, request_user_input, create_goal, get_goal, update_goal`，以及 `collaboration` 下的 `spawn_agent, wait_agent, send_message, list_agents, interrupt_agent, followup_task` |
| DSH（29） | `working_directory, read, read_image, glob, grep, write, edit, bash, job_list, job_output, job_kill, todo_write, create_goal, get_goal, update_goal, exit_plan_mode, skill, workflow, spawn_teammate, list_agents, send_message, wait_agent, interrupt_agent, team_task_create, team_task_get, team_task_list, team_task_update, web_search, web_fetch` |
| Nanobot（23） | `list_dir, find_files, grep, read_file, write_file, write_file_chunk, edit_file, apply_patch, exec, exec_session, list_exec_sessions, run_cli_app, spawn, list_sessions, read_session, search_sessions, send_session_message, message, my, create_goal, update_goal, web_search, web_fetch` |
