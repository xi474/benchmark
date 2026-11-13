# 四Harness显式委派：Medium20＋修订六题的已完成结果与监控审计

发布快照：2026-11-13。**205个有分结果已逐项离线核验（101显式＋104历史原生对照）；另3个Codex无分题位仅登记待补，不发布补跑中的指标。** 显式组104个逻辑题位中，87个正常有分、14个预算异常但有完整评分、3个无分。原始attempt、失败门禁和原始分数保留。

**模式限定：Codex的49个有分结果请求`reasoning.effort=none`，但原生轨迹出现reasoning，实际非思考模式未证实。†标记仅供存档和描述性比较，不进入“严格普通模式”的已验证排名。** 其他Harness登记为`thinking.disabled`且未发现同类矛盾；这不声称测得模型内部推理过程。

## 实验范围与对照边界

- Harness为Nanobot、OpenCode、Codex、DSH。LATTE/LangGraph未加入本轮显式委派干预；正式baseline仍为原六套，ROMA/AOrchestra/SDK不在本报告矩阵中。
- `medium20-original`是原Medium26剔除MP04/08/09/10/11/24后保留的20题：MP01/02/03/05/06/07/12/13/14/15/16/17/18/19/20/21/22/23/25/26。**不是仓库2026-11-13新发布的`parallel20-calibrated-medium-v1`。**
- `adapted6-core-v3`是另行修订的MP04/08/09/10/11/24，Git tree为`e5dcfe62aec12bad2dd9eac3cbec36184a22fe07`；24个显式结果按任务、模型、配置和限额一致性复用，未重跑。
- 本次保留实际运行时的score-v2 / original-core-v3政策，单题上限2；**未按仓库后续50%完整交付政策重评**。`verifier_checks.csv`保留核心与optional检查分类，API准确率只统计`api/`检查，不是供应商HTTP成功率。
- 显式条件要求至少两个有实际工作的子Agent并由父Agent汇总/验证；实际完成情况按原生父子身份、独立模型/工具和回传分别核验。历史原生对照104格均未观测子创建，但没有强制禁用能力，**不是强制单Agent消融**。
- 新Medium20队列自身最多5个Harbor trial、根及子模型请求共享HTTP4；用户允许外部批次并行，因此不是全机器HTTP4。历史对照非同期、非随机化，不能将差异直接解释为multiagent的因果收益。
- 输出上限Nanobot/OpenCode为8192，Codex/DSH为32768。新Medium20不新增累计token cap；修订六题Nano/OpenCode沿用历史2M保护、Codex/DSH没有该累计保护。两层数据及预算分别报告。

## API、耗时与子创建

以下所有均值、用量和子身份只取本次发布的205个有分结果；预算异常有分保留标签，不作为正常结束。未评分题不填零、不加入质量分母。逐任务结果见[completed_cells.csv](completed_cells.csv)，全部题位状态见[matrix_status.csv](matrix_status.csv)。

| 条件 | Harness | 数据集 | 有分题 | API通过/总数 | API微平均 | 平均E2E秒 | 平均Agent秒 | 平均评分秒 | 有子题/有分题 | 子ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 显式 | Nanobot | medium20-original | 20 | 393/506 | 77.67% | 670.7 | 649.5 | 10.2 | 20/20 | 55 |
| 显式 | Nanobot | adapted6-core-v3 | 6 | 138/142 | 97.18% | 498.7 | 469.9 | 16.6 | 6/6 | 14 |
| 显式 | OpenCode | medium20-original | 20 | 214/506 | 42.29% | 236.5 | 215.6 | 10.5 | 12/20 | 30 |
| 显式 | OpenCode | adapted6-core-v3 | 6 | 114/142 | 80.28% | 212.1 | 184.4 | 16.2 | 5/6 | 11 |
| 显式 | Codex† | medium20-original | 17 | 331/436 | 75.92% | 1570.0 | 1548.0 | 10.2 | 16/17 | 48 |
| 显式 | Codex† | adapted6-core-v3 | 6 | 142/142 | 100.00% | 1049.4 | 1021.8 | 14.1 | 6/6 | 18 |
| 显式 | DSH | medium20-original | 20 | 400/506 | 79.05% | 563.4 | 541.5 | 10.4 | 20/20 | 47 |
| 显式 | DSH | adapted6-core-v3 | 6 | 130/142 | 91.55% | 409.6 | 367.1 | 24.1 | 6/6 | 14 |
| 历史原生 | Nanobot | medium20-original | 20 | 401/506 | 79.25% | 983.5 | 948.7 | 17.3 | 0/20 | 0 |
| 历史原生 | Nanobot | adapted6-core-v3 | 6 | 137/142 | 96.48% | 362.9 | 325.4 | 21.7 | 0/6 | 0 |
| 历史原生 | OpenCode | medium20-original | 20 | 161/506 | 31.82% | 296.1 | 263.6 | 17.6 | 0/20 | 0 |
| 历史原生 | OpenCode | adapted6-core-v3 | 6 | 59/142 | 41.55% | 118.0 | 82.5 | 22.0 | 0/6 | 0 |
| 历史原生 | Codex† | medium20-original | 20 | 447/506 | 88.34% | 1644.7 | 1607.5 | 18.0 | 0/20 | 0 |
| 历史原生 | Codex† | adapted6-core-v3 | 6 | 142/142 | 100.00% | 1035.1 | 1001.8 | 16.4 | 0/6 | 0 |
| 历史原生 | DSH | medium20-original | 20 | 414/506 | 81.82% | 687.2 | 652.2 | 18.1 | 0/20 | 0 |
| 历史原生 | DSH | adapted6-core-v3 | 6 | 111/142 | 78.17% | 509.8 | 483.4 | 14.3 | 0/6 | 0 |

E2E统一重算为原始Harbor `finished_at-started_at`，包括环境/安装、Agent、verifier和收尾，不包含入队等待。Agent和verifier是独立原生阶段时间，二者之和不必等于E2E；模型与工具可能重叠，也不能与E2E相加。历史报告采用不同外层时钟时，本包以这里的Harbor原始起止为准。

## tokens、缓存与成本

| 条件 | Harness | 数据集 | 输入tokens | 输出tokens | 缓存输入tokens | 输入缓存率 | 已结算估算USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 显式 | Nanobot | medium20-original | 46,291,927 | 846,265 | 45,492,864 | 98.27% | 6.407659 |
| 显式 | Nanobot | adapted6-core-v3 | 10,878,723 | 185,432 | 10,623,104 | 97.65% | 1.539144 |
| 显式 | OpenCode | medium20-original | 9,608,304 | 284,062 | 9,182,336 | 95.57% | 2.091186 |
| 显式 | OpenCode | adapted6-core-v3 | 3,794,073 | 93,722 | 3,613,440 | 95.24% | 0.768566 |
| 显式 | Codex† | medium20-original | 73,392,706 | 1,654,767 | 71,780,736 | 97.80% | 11.839030 |
| 显式 | Codex† | adapted6-core-v3 | 23,865,233 | 510,942 | 23,431,424 | 98.18% | 3.626941 |
| 显式 | DSH | medium20-original | 25,954,892 | 692,964 | 25,071,744 | 96.60% | 5.013050 |
| 显式 | DSH | adapted6-core-v3 | 6,888,302 | 159,093 | 6,632,192 | 96.28% | 1.259890 |
| 历史原生 | Nanobot | medium20-original | 39,787,682 | 709,673 | 39,371,136 | 98.95% | 5.092476 |
| 历史原生 | Nanobot | adapted6-core-v3 | 9,024,222 | 155,877 | 8,912,000 | 98.76% | 1.157534 |
| 历史原生 | OpenCode | medium20-original | 5,134,600 | 197,578 | 4,936,960 | 96.15% | 1.260520 |
| 历史原生 | OpenCode | adapted6-core-v3 | 1,344,880 | 51,380 | 1,275,520 | 94.84% | 0.351143 |
| 历史原生 | Codex† | medium20-original | 64,359,437 | 1,776,886 | 63,512,448 | 98.68% | 10.949042 |
| 历史原生 | Codex† | adapted6-core-v3 | 12,492,787 | 375,260 | 12,329,088 | 98.69% | 2.244592 |
| 历史原生 | DSH | medium20-original | 22,477,887 | 716,645 | 22,025,088 | 97.99% | 4.404713 |
| 历史原生 | DSH | adapted6-core-v3 | 4,158,332 | 168,954 | 4,047,104 | 97.33% | 0.993951 |

- 输入tokens已包含缓存输入；总tokens=输入＋输出。reasoning是输出子集，不重复相加；缺字段保留空，已知reasoning和配套字段覆盖率一起看，不能把部分已知和当完整总量。
- 输入缓存率=已结算请求缓存输入总和/输入总和，是供应商API报告的缓存token比例，不是底层KV-cache容量、逐层或逐请求二值命中率。
- 每个模型请求按网关ID去重，导出为不可逆`request_ref`；10552个已结算请求可在[request_usage.csv](request_usage.csv)逐项核对。本包205个有分结果的已结算用量未知数为0，**不代表整个实验历史没有未知请求**。
- 成本保留运行时价格快照估算：每百万输入miss USD1.32、缓存输入USD0.044、输出USD3.96，公式为`((input-cache)*1.32 + cache*0.044 + output*3.96)/1e6`。**不是账单，也不声称是谷价结算**。
- 本包101显式有分结果已知估算USD32.545465480；全部205个有分结果含历史对照估算USD58.999436056。这两个是题位选择口径，不能相加。
- [batch_costs.json](batch_costs.json)另记原R1/R2物理新批：5237发出、5227结算、10未知，已知估算USD28.140771736；含被替代失败attempt，不含24个历史修订六题复用成本。它与本包选定结果成本口径不同，**不能相加或视为实际总账单**。后续修复补跑attempt的指标与费用待其完成后独立追加。

## 同题配对

101对双方有分结果逐项核对API检查ID集合相同，不能用Codex显式17题的分母与原生全部20题的分母直接比较。另3对待补仅登记状态。

| Harness | 数据集 | 同题同API分母的配对数 | 原生API | 显式API | 原生/显式平均E2E秒 |
| --- | --- | --- | --- | --- | --- |
| Codex† | adapted6-core-v3 | 6 | 142/142 | 142/142 | 1035.1 / 1049.4 |
| Codex† | medium20-original | 17 | 389/436 | 331/436 | 1605.3 / 1570.0 |
| DSH | adapted6-core-v3 | 6 | 111/142 | 130/142 | 509.8 / 409.6 |
| DSH | medium20-original | 20 | 414/506 | 400/506 | 687.2 / 563.4 |
| Nanobot | adapted6-core-v3 | 6 | 137/142 | 138/142 | 362.9 / 498.7 |
| Nanobot | medium20-original | 20 | 401/506 | 393/506 | 983.5 / 670.7 |
| OpenCode | adapted6-core-v3 | 6 | 59/142 | 114/142 | 118.0 / 212.1 |
| OpenCode | medium20-original | 20 | 161/506 | 214/506 | 296.1 / 236.5 |

这组观察没有显示“显式触发后必然更准确或更快”；任务、预算异常、历史运行环境及Codex模式疑点都限制解释。[paired_cells.csv](paired_cells.csv)提供逐对原始指标，[paired_summary.csv](paired_summary.csv)提供微/宏统计所需分母。

## 运行指标覆盖率与缺失

**核心质量、E2E/Agent/verifier、已结算tokens/cache/估算费用、模型HTTP elapsed和任务容器资源样本205/205齐全；全量逐请求工具/提示监控、真实进程并行及自检增量开销没有达到统一完整覆盖。** 不把“可上传已核验数据”写成“全部监控指标均已测得”。逐格状态见[coverage.csv](coverage.csv)和[METRICS.md](METRICS.md)。

| Harness | 有分题 | 容器资源覆盖 | 模型HTTP耗时完整 | 工具span时间完整 | 识别到检查命令的题数 | 工具清单有未知名称的题数 | 无提示指纹的题数 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nanobot | 52 | 52 | 52 | 52 | 51 | 20 | 6 |
| OpenCode | 52 | 52 | 52 | 52 | 29 | 0 | 6 |
| Codex† | 49 | 49 | 49 | 0 | 47 | 0 | 0 |
| DSH | 52 | 52 | 52 | 52 | 0 | 0 | 0 |

- 205格均有至少两个可比task-container cgroup样本，导出采样数、窗口、采样内存峰值和CPU累计差；采样峰值不是整个生命周期的硬件峰值，逐子Agent资源按原设计未采集。
- 模型HTTP耗时是每个已结算请求的网关上游elapsed，包含供应商/网络等延迟、排除网关准入等待；并发时求和可大于E2E，不叫纯模型计算耗时。
- Nanobot/OpenCode/DSH的156格可配对工具span并计算同钟域union；Codex49格缺可比工具起止，不能用日志接收时间、UI事件时长或`write_stdin`返回的墙钟片段拼成完整执行时间。后台进程关联记录单列，未恢复的完整进程时长保持未知。
- 工具span可包含`task`/spawn/wait等编排；leaf工具span峰值也不是操作系统进程真实重叠证明。不能据子ID数、HTTP槽或span峰值宣称真实工具并行。
- 20格历史Nanobot请求清单含未知名称，12格历史Nano/OpenCode没有提示指纹。保留已观测工具名、指纹数和缺失数，**不倒推成完整实际请求schema或权限证明**；原配置意图和实际模型开放工具不可混同，也不为补取证重跑付费结果。
- 127格捕获到可识别检查命令；43个失败检查关联窗口中，16个有“检查失败→修复活动→复验”的关联，27个证据不完整。识别依据工具输入/显式检查及结果字段，不读取或公开思维链。命令未识别不是没有自检，未观测失败分析不是没有分析；窗口耗时不是纯自检增量时间/费用。

## 子Agent工作与回传证据

本包237个子身份均来自有分结果，不含三个无分旧题的9个子身份。235个有自身模型工作证据，2个未知；创建、工作、父接收及进入后续请求分别记账。

| Harness | 有分题子ID | 独立模型工作已观测 | 模型工作未知 | 工具记录已观测 | 父接收已观测 | 父接收未知 | 后续请求已观测 | 后续请求未知 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nanobot | 69 | 69 | 0 | 69 | 18 | 51 | 0 | 69 |
| OpenCode | 41 | 41 | 0 | 41 | 41 | 0 | 41 | 0 |
| Codex† | 66 | 64 | 2 | 53 | 62 | 4 | 62 | 4 |
| DSH | 61 | 61 | 0 | 61 | 0 | 61 | 0 | 61 |

未知不是未发生。OpenCode从原生SQLite递归parent_id并排除空assistant占位；Codex从native thread parent和独立去重usage读取，父接收与后续请求分别核对；Nanobot使用实际`agent.run.started`，DSH的统一回传消息链覆盖有限。工具记录包括失败/待定状态，不能直接当作成功工作或真实并行。详见[agents.csv](agents.csv)。

## 终态、待补与发布范围

- 显式预算异常14格：Nano修订六题MP04/08/10累计2M保护；OpenCode修订MP04及Medium20 MP03/06/13/14/16/19/20/26响应上限；Codex Medium20 MP20/22响应上限。原始标签与审计标签并存，不按低分选择性重跑。
- 原生对照的预算/超时异常也保留在逐格终态字段，不能把104个有分都称正常完成。
- Codex Medium20 MP15/MP17/MP19的原无分状态分别为连接/超时、连接失败、上游HTTP400；**不当模型质量0分**。本次只发布其轻量待补身份；后续修复attempt仍未获合格评分，MP15/MP17尚未进入新队列执行，补跑指标尚未发布。
- Codex52格原生/显式模式审计范围含上述3个无分，49个有分在本包；`none`与实际reasoning矛盾保留。旧三档报告的soft-reminder不在这52格审计范围内，不能外推为已核验。

本次上传仅脱敏汇总、检查项、请求用量、来源哈希和覆盖率；不公开原始prompt、思维链、候选代码、完整会话、API key或私有MLP-PPT24。原件在本地保留，公开哈希便于持有原件者核对；公开包的独立校验验证内部一致性，不替代重新执行verifier。

## 离线验收与文件

运行`python verify.py`，无需依赖、网络或付费模型。脚本核对SHA256、205格唯一性、10552请求去重、逐项API分母、Harbor时间、tokens/cache/价格快照、237子身份和101对同检查ID集合。

- [validation.json](validation.json)：本地原件SHA/API/时间/用量核验和覆盖率，明确`all_runtime_metrics_uniformly_complete=false`。
- [completed_cells.csv](completed_cells.csv) / [summary.csv](summary.csv)：逐任务和Harness×条件×数据集汇总。
- [verifier_checks.csv](verifier_checks.csv)：逐项检查ID、类别、通过位及原score SHA。
- [request_usage.csv](request_usage.csv)：逐已结算请求用量与HTTP elapsed，不含请求正文。
- [coverage.csv](coverage.csv) / [self_check_loops.csv](self_check_loops.csv)：缺失状态与自检关联窗口；空值不填零。
- [agents.csv](agents.csv)：原生子身份、自身工作及回传阶段的正向证据/未知。
- [provenance.json](provenance.json)：相对来源身份、冻结manifest/result/score哈希；不含个人绝对路径。
- [matrix_status.csv](matrix_status.csv)：208个逻辑行的有分/待补标记。
- [SHA256SUMS](SHA256SUMS) / [verify.py](verify.py)：公开包完整性及离线一致性验收。
