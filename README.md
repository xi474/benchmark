# SemServe Agent-Parallelism 18-Entry Task Pack

<!-- DSH-CROSS-DATASET-COMPARISON-20261117 -->
## DSH跨任务集单Agent／委派策略对照：v4导读版

**[最新报告、图表及同事审阅包](results/dsh-cross-dataset-comparison-20261117/README.md)** · [修订报告](results/dsh-cross-dataset-comparison-20261117/revisions/v4-overview/DSH单多Agent跨任务集对照报告.md) · [v4审阅包下载](results/dsh-cross-dataset-comparison-20261117/downloads/DSH对照实验-同事审阅包-20261117-v4导读版.zip)

先解释R3参考分工、LATTE原题、Mabench强制／可选委派及Complex10三组各做了什么、目的与结论，再展开API／功能、E2E、tokens/cache及估算成本。L114同一道题的两次配对重测A（原重复2·协议v3）与B（原重复1·事务冻结v4）分别说明，资源不跨版本混算；Complex的M强制至少1工作子，Mabench多需求M允许自主决定、最低0。原130条主对照、145／153条运营记录与全部数值不变，旧版报告、既有结果和异常说明保留；费用估算非账单。

<!-- /DSH-CROSS-DATASET-COMPARISON-20261117 -->

<!-- DSH-MODULAR20-COMPARISON-20261117 -->
## 同事模块化20题：DSH委派与自研Harness综合对比

**[完整报告与统一指标总表](results/dsh-modular20-delegation-harness-comparison-20261117/README.md)** · [显式与未显式M103同题对照](results/dsh-modular20-delegation-harness-comparison-20261117/显式委派与未显式要求_同题对照.md) · [同10题不同模式](results/dsh-modular20-delegation-harness-comparison-20261117/10题不同Harness模式_统一指标对比.md)

两部分均列严格通过率、核心转换用例通过率、50%交付reward、E2E、根子token与统一峰价成本。M103原样／显式各一次、均满分且真实子0／2；同10题reward：自研普通OFF7.25、DSH普通新提示15.75、自研普通ON17.50、自研High OFF20.00（满分20）。附8组PNG/SVG、逐题计分、来源核对和局限；本次新启动的DSH High20题仅列独立进度快照，不混算已完成结果。费用为估算，计时、恢复和控制条件未完全一致，不作因果排行榜。

<!-- /DSH-MODULAR20-COMPARISON-20261117 -->

<!-- DSH-TAU-MABENCH-20261115 -->
## DSH在τ-bench/Mabench上的受控委派对照与trace分析

**[12次结果、图表与阶段异常](results/dsh-tau-mabench-v4pro-20261115/README.md)** · [逐次指标](results/dsh-tau-mabench-v4pro-20261115/cells.csv) · [192条usage](results/dsh-tau-mabench-v4pro-20261115/request-usage.csv)

V4 Pro普通、四Harbor/HTTP4。12次全部处理，R1四次对话适配截断、R2四次完整但M0子、R3四次独立强委派分列；R3 S/M均2/2成功，M两题各2名有工作子并有真实请求交叠，但完整E2E+26.0%、tokens+35.3%、估算费用+147.3%。trace显示查询粒度小、第2题重复库存调查且后续退货需求较晚公开；每格1次，不作稳定因果结论。含5张PNG/SVG、缓存与费用分量、原生时间线和脱敏证据；费用估算非账单，不混用API语义准确率或本仓库50%交付奖励。全部旧报告保留。

<!-- /DSH-TAU-MABENCH-20261115 -->


<!-- DSH-LATTE-ORIGINAL12-20261115 -->
## DSH在LATTE原始两任务上的单／多Agent对照

**[12次完整图表报告](results/dsh-latte-original-tasks-v4pro-20261115/README.md)** · [逐次数据](results/dsh-latte-original-tasks-v4pro-20261115/cells.csv) · [可复核指标](results/dsh-latte-original-tasks-v4pro-20261115/metrics.json)

V4 Pro普通模式、四Harbor/HTTP4，TP模块扩展与DBG调试各S/M三次。12/12有原功能分、288/288结算unknown0；M6/6各建两名实际工作子，S0子。TP部分功能通过率74.7%→82.7%，两组均0/3整题全过；DBG均100%。两任务等权宏平均87.3%→91.3%，但平均完整E2E+28.2%、tokens+132.7%。附五张PNG/SVG、全量配对、原生span、资源、缓存及计价数据；保留精确子结果后续输入匹配未知、并发争用和小样本限制。费用估算非账单；不运行LATTE Harness，不覆盖旧R1/R2/R3。

<!-- /DSH-LATTE-ORIGINAL12-20261115 -->


<!-- DSH-REFERENCE-R3-20261115 -->
## DSH R3单与多Agent三维收益对照

**[R3完整报告与三维收益图](results/dsh-reference-decomposition-v4pro-20261115-r3/README.md)** · [逐次指标](results/dsh-reference-decomposition-v4pro-20261115-r3/cells.json) · [同题配对](results/dsh-reference-decomposition-v4pro-20261115-r3/paired-comparison.json) · [R2历史结果](results/dsh-reference-decomposition-v4pro-20261115-r2/README.md)

12/12结束、11有分及1次评分器超时；多Agent6/6真实创建子。收益分Accuracy、完整E2E与tokens：双方有分同一5对，S/M为98.3%/91.7%、565.8/665.6秒、1158/1975万tokens。局部有用协作与效率收益存在，未见稳定整体净收益。保留残留误拦、自编验证错误、共享HTTP4排队、R1/R2和历史unknown；新R3账本788/788结算unknown0，费用估算非账单。

<!-- /DSH-REFERENCE-R3-20261115 -->

<!-- DSH-REFERENCE-R2-20261115 -->
## DSH单／多Agent参考分工对照（2026-11-15）

**[修复版R2图表报告](results/dsh-reference-decomposition-v4pro-20261115-r2/README.md)** · [逐次指标JSON](results/dsh-reference-decomposition-v4pro-20261115-r2/cells.json) · [协议异常与重测建议](results/dsh-reference-decomposition-v4pro-20261115-r2/protocol-notes.md) · [修复前R1历史结果](results/dsh-reference-decomposition-v4pro-20261115-r1/README.md)

三题各S/M两次，12/12已处理；严格单Agent API65/72，多Agent在4个有评分试次中48/48，另有2次无评分且有分中1次协议异常，不能解释为六次全部成功。多Agent6/6真实建子，有M103的发现—修复—复验案例，但未证明决定性整体提升或稳定时间／成本双收益。附5张PNG及SVG、完整E2E阶段拆分、tokens/cache、已知估算成本与原生证据摘要；异常、控制层误拦及1笔未知用量保留，费用非账单。R1/R2分列，不改题／评分器或旧成绩。

<!-- /DSH-REFERENCE-R2-20261115 -->

## 新增：实测中档20题（2026-11-13）

[20题独立发布包](parallel20-calibrated-medium-v1/README.md)：20个不同题族，每题经Terminus 2＋DeepSeek V4 Pro普通模式五次有效运行、严格通过2–3/5及核心失败复核后接纳。

- [中文目录与逐题说明](parallel20-calibrated-medium-v1/docs/20题目录.md) · [来源说明](parallel20-calibrated-medium-v1/docs/来源说明.md) · [ASCI评审](parallel20-calibrated-medium-v1/docs/ASCI评审.md)
- [20张DAG及Mermaid](parallel20-calibrated-medium-v1/docs/DAG.md) · [100次五测结果](parallel20-calibrated-medium-v1/docs/五次实测结果.md) · [Agent-only下载](parallel20-calibrated-medium-v1/downloads/agent-only.zip)

原题、初始工作区、评分器及原始成绩按冻结版本保留；结构档与实测档分列。只向Agent提供单题TASK.md与workspace；作者材料在外部。此新增包独立于下方历史集合统计，同来源族的不同版本不重复计题。


## 新增30题核心版与并行预测器完整信息（2026-11-11）

**[30题完整数据集](medium30-core-v1/README.md)** · **[30题中文目录及实际DAG](medium30-core-v1/docs/30题目录与实际DAG.md)** · **[并行预测器JSONL数据](medium30-parallel-prediction-v1/README.md)** · [发布与数据通路核验](medium30-parallel-prediction-v1/发布与通路核验.md)

新增30道不同题目、94个组件；SWE-bench Verified 11题、SWE-bench Pro 8题、Terminal-Bench 7题、GAIA2 4题。全部以中等为结构设计目标，实测档位待校准。包含题面、输入、SPEC、contract、workflow、来源及原始难度、参考解、外部verifier、作者QA及冻结哈希。

- [下载完整30题包](medium30-core-v1-full.zip)、[Agent初始包](medium30-core-v1-agent.zip)、[Harbor执行包](medium30-core-v1-harbor.zip)、[预测器补充包](medium30-parallel-prediction-v1.zip)。
- 预测器数据：30任务、94组件、71条直接依赖、102组件对及150静态就绪状态；附完整信息索引、文本特征视图和独立标签。30/30参考解按导出DAG执行检查通过。
- 补充标签描述组件执行的数据依赖，不是Agent编码顺序或实测加速比。训练时按题目/来源分组，避免把依赖真值直接作为输入。盲测只给单题TASK和初始workspace，参考解/verifier/DAG在Agent工作区外。


## 统一评分标准：50%完整交付奖励

采用 **50%核心验收完成分＋50%整题严格通过奖励**，单题上限按发布前冻结的E/M/H权重1/2/3确定。公开通过、**核心转换用例通过率**（原API acc）与严格通过分别报告。

**[正式评分规范 v1.0](docs/scoring/统一评分标准_v1.0.md)** · [机器可读规则](docs/scoring/reward-policy-v1.0.json) · [合成计分示例](docs/scoring/examples-v1.0.json)

规范已采纳；已有数据包的旧评分器尚未自动迁移。实施须独立冻结评分版本及检查清单；任务内容与历史成绩保留。仅对旧记录重算50%权重，不等同于通过新增严格验收。

<!-- EXPLICIT-ACCURACY-TRACE-20261113 -->
## 显式委派与原生执行的 API 准确率变化：trace 归因

[104 对结果、逐 API 检查与退化机制分析](results/explicit-vs-native-accuracy-trace-analysis-20261113/README.md)：Medium20 的下降并非普遍；Codex 净少通过的 58 个检查由 MP20／MP22 输出上限异常完整核算，正常任务主要见公共契约和验收遗漏。保留正式预算异常成绩、旧 Codex 实际模式疑点／R7 适配分层及 MP03／MP22 规格歧义，不作 multiagent 天然降低能力的因果结论。附 2,592 个检查位、来源 SHA、trace 事件索引及离线校验器；不改原始分数。

<!-- /EXPLICIT-ACCURACY-TRACE-20261113 -->

<!-- CODEX-R7-COMPLETED-20261113 -->
## Codex三个缺分题位补齐（R7独立修复版）

[MP19/MP15/MP17完整补跑与监控报告](results/explicit-medium20-codex3-chat-normal-r7-20261113/README.md)：3/3有效有分，API58/70（82.86%），先MP19 pilot后自动并行其余两题。新适配层1.0.4实际Chat thinking.disabled；权限、提示、题/verifier不变。旧205行快照、失败attempt和13条历史未知保留；旧Codex模式疑点不被新3题覆盖，不作跨适配层严格同配置排名。

<!-- /CODEX-R7-COMPLETED-20261113 -->

<!-- EXPLICIT-MATRIX-20261113 -->
## 四Harness显式委派与原生对照（2026-11-13已完成结果审计）

[Medium20原保留集＋修订六题：结果、API、E2E、tokens/cache、资源与覆盖率](results/explicit-medium20-core6-four-harness-v4pro-20261112/README.md)：101个显式有分＋104个历史原生有分，另3个Codex题位待补且未纳入补跑指标。核心指标205/205可核对；工具时间156/205，真实进程并行/自检增量不可统一观测，缺失单列。Codex49个有分结果的实际普通模式未证实，不作严格普通模式排名。保留原score政策，未按50%交付政策重评；这里的Medium20不是新`parallel20-calibrated-medium-v1`。

**对下方旧DSH/Codex报告的模式勘误：** Codex原生/显式请求none但原生轨迹出现reasoning；旧“实际non-thinking”表述不再视为已验证结论，原分数及子创建原件保留，soft条件未在本次52格范围核验。

<!-- /EXPLICIT-MATRIX-20261113 -->

## Nanobot/OpenCode三档提示实验（2026-11-11）

[修订六题36格完整报告](results/core6-nanobot-opencode-three-conditions-v4pro-20261111/README.md)：V4 Pro普通模式，复用12原生格、新增24；36有分、22正常／14异常。显式委派下Nanobot6/6题共14子，OpenCode5/6题共11子；原生／软提醒与预算截断分别报告。含逐任务API核心转换用例通过率、统一Harbor E2E、tokens、输入缓存和估算费用，保留original-core-v3评分。

## DSH/Codex运行时子Agent检测（2026-11-11）

[修订六题三条件36格结果](results/core6-dsh-codex-three-conditions-v4pro-20261111/README.md)：V4 Pro普通模式，复用25格、补缺11格；35有分、1无分。显式委派两套Harness各6/6触发，原生/软提醒与预算截断分列，附API准确率、E2E、tokens、缓存与估算费用。保留original-core-v3评分，未按50%交付奖励重评。

## 数据集入口：改编26题已同步到 main

**[独立六题v3五次复测分档汇总](results/adapted6-core-v3-terminus2-v4pro-five-20261109/README.md)**：30/30次完成，核心成功14/30；易1题、中3题、难2题。仅公开脱敏汇总，通用稳健性单独记录。

- **[独立六题核心版 v3（本轮复测入口）](adapted6-core-v3/README.md)**：核心业务完成与通用稳健性分开评分；[六题目录与DAG](adapted6-core-v3/docs/六题中文目录与DAG.md)、[新评分与难度规则](adapted6-core-v3/docs/难度分级标准_v3.md)、[下载Agent包](adapted6-core-v3-agent.zip)、[下载完整包](adapted6-core-v3-full.zip)。这是原MP04/08/09/10/11/24的独立新版本；原26题包及v2成绩保留，不新增题型数量。

- **[改编26题 v2：20题原版 + 6题修订版](medium26-extension-v2/README.md)**：26题统一入口，共93个组件；[直接浏览任务](medium26-extension-v2/tasks/)、[26题中文目录和DAG](medium26-extension-v2/docs/26题中文目录与DAG.md)、[下载Agent任务包](medium26-extension-v2-agent.zip)、[下载完整包](medium26-extension-v2-full.zip)。
- [六题独立修订集](medium6-specfix-v2/README.md)：MP04、MP08、MP09、MP10、MP11、MP24；[下载六题Agent包](medium6-specfix-v2-agent.zip)。这是上述26题的子集，便于单独复测。
- [原始14题](tasks/)：原始suite共18个入口、14个不同题目。
- [Mixed16 精确规格 v4](mixed16-precise-spec-v4/README.md)：16道独立扩展题。
- [同事新增 Long Parallel10](long-parallel10-10r-20261104/README.md)：独立的10题、30组件任务集。

原14题 + Mixed16的16题 + 本改编26题，共56道不同题目；六题独立包作为版本子集统计，同事新增10题另行统计。26题中的20题TASK/初始workspace与v1逐字节一致，6题采用已发布修订版，见[逐题组成核对](medium26-extension-v2/review/distribution_composition.json)。

26题均附来源与原始难度标注、作者DAG、独立正式verifier和小数reward评分器。使用时只向Agent提供单题TASK.md与初始workspace；作者材料和verifier放在Agent工作区外。Medium26/M保留历史设计目标，实测难度按对应版本的baseline另行记录。此前这批材料位于工作分支，本入口于2026-11-09同步到main。


This package contains the original task prompts and initial workspaces used by
the Retest18 experiment. It is intended for evaluating whether an agent harness
can discover dependency structure and parallel opportunities during execution.

## Dataset shape

- 18 benchmark entries across four suites: `multistage4`, `reasoning4`,
  `context8`, and `linux2`.
- 14 unique task names. Four workloads intentionally occur in both
  `multistage4` and `context8`, preserving the historical experimental suites.
- Every entry contains `TASK.md` and an untouched initial `workspace/`.

## No topology leakage

The package intentionally excludes experiment-side `case.json` files, planned
DAGs, frontier timing rules, expected classifier labels, traces, model outputs,
and execution results. A harness should give the model the task text and the
initial workspace only. Any dependencies or parallel opportunities must be
discovered online.

## Running an entry

1. Send `TASK.md` as the user request.
2. Mount or copy `workspace/` as the agent's working directory.
3. Let the harness execute the task without reading hidden experiment metadata.
4. When a root `check.py` exists, run `python check.py` after the agent finishes.

`manifest.json` records task counts and SHA-256 digests for reproducibility.

## Mixed16 extension (v3)

The separately versioned [Mixed16 v3 extension](mixed16-extension-v3/README.md)
adds 16 unique tasks: four each in the `multistage4`, `reasoning4`, `context8`,
and `linux2` styles. Its [manifest](mixed16-extension-v3/manifest.json) and
checksums are independent of the original 18-entry manifest at the repository root.

The extension combines file dependencies with constrained scheduling, stateful
recovery, compatibility checks, and graph algorithms. Author validation covers
all 16 reference solutions, 452 API cases, 82 rejected mutations, and 56 small
independent algorithm checks. These are correctness checks, not measured agent
performance results.

For an evaluation, provide only one task's `TASK.md` and initial `workspace/`.
Keep the extension's `_authoring/` and `verifier/` directories outside agent
mounts; they contain reference algorithms, hidden checks, and trusted hashes.
Local `check.py` is a smoke test; official scoring uses the external verifier.
Do not mount the whole repository as an agent workspace.

### Component DAG gallery

[Browse the DAGs for all 16 Mixed16 v3 tasks](mixed16-extension-v3/_authoring/dags/README.md).
Each task includes SVG/PNG diagrams, editable Mermaid source, and validated
dependency data. Diagrams are author-only metadata; keep them outside agent
mounts along with the rest of `_authoring/`.

## 原30题来源与改编追溯（2026-11-13）

[逐题中文来源说明](medium30-core-v1/docs/原题来源与改编说明.md)：N01–N30对应31个源实例，保留SWE-bench Verified、SWE-bench Pro、Terminal-Bench和GAIA2各自的原始标签、固定revision、修复前基线与改编范围。另有[JSON/CSV可联结索引](medium30-core-v1/review/source_provenance_v1.json)。本次仅补来源文档，不改题目、verifier或既有成绩。
