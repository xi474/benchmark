# 哪些运行机制值得 SP 借鉴，它们用什么换取更可靠的交付？

2026 年 11 月 23 日 · Upstream59 v2.1.0 · DeepSeek V4 Pro 普通模式 · Codex、DSH、SemanticParallel 源码与原生 trace 离线复核

## 结论

**首选验证两项改动。一项是让根 Agent 能接回仍在运行的验证进程，拿到退出码和增量输出。另一项是让根 Agent 覆盖已有文件时校验它上次看到的版本，特别是合并子分支之后。** 前者解决“长验证怎样做完”，后者解决“正在修改哪一版”。两项都有原生事件可核对，也都有能在低成本离线回放中检验的失效条件。它们补充了此前提出的局部编辑、根工作区整体验证和协议失败恢复。另有两个较窄的方向值得做对照，即普通业务轮可维护的交付清单、长任务跨上下文窗口的语义交接。[此前改进方案](sp-accuracy-reward-improvement-plan-20261123.md)

**最能解释历史 Reward 差距的量，是整题严格通过。** SP 和 DSH 首轮同为 633/803 项核心 API 通过，DSH 却多严格通过 11 题，多得 12.693496 分，其中 12 分来自严格通过加分。Codex 比 SP 多得 18.837334 分，其中 14.5 分来自严格通过加分。下面四项运行机制都有使用证据，现有数据无法把这些分数分摊给某个工具。尤其要保留 SP 的速度优势。逐题配对，首轮 SP 的执行阶段在 51/59 题短于 Codex，在 46/59 题短于 DSH。[复算与逐题配对](evidence/sp-tradeoff-evidence.json) · [59 题发布原表](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

**要先试一项直接针对准确率的改变，我会选“按公开语义独立出期望答案，并把它和完整候选实现逐例比对”。** MS41 暴露了一个具体问题。SP 的两个分支各自写了测试，根也通过了公开检查，但整合时把“每轮抽一次环境”算成了“每张票重新抽环境”。DSH 在这题真的运行了 500 例独立参考对照。这个策略可以直接用 SP 现有工具验证，实验里要与“能否续接长验证”分开开关。第 4 节还原了三条轨迹及验证本身出错的情形。

## 1. 跨系统实际换来了什么

| 59 题 | SP 首轮 | SP 首轮加公开失败重放 | Codex | DSH |
|---|---:|---:|---:|---:|
| 核心转换 API 检查 A | 633/803（78.83%） | 669/803（83.31%） | 683/803（85.06%） | 633/803（78.83%） |
| 整题严格通过 | 25/59 | 28/59 | 38/59 | 36/59 |
| Reward，满分 138 | 78.469237 | 85.361619 | 97.306571 | 91.162733 |
| 其中，严格通过加分 | 28.5 | 32.0 | 43.0 | 40.5 |
| 执行阶段中位数，秒 | 247.95 | 317.12 | 716.68 | 426.04 |
| 完整 Harbor E2E 中位数，秒 | 未知 | 未知 | 749.57 | 458.67 |
| 已知输入 / 输出，百万 token | 179.929 / 1.765 | 209.898 / 2.037 | 102.672 / 3.327 | 45.773 / 1.601 |
| 已计量输入缓存命中率 | 90.12% | 89.99% | 98.22% | 97.31% |
| DeepSeek 请求数 / 缺用量数 | 4,361 / 14 | 5,116 / 15 | 2,137 / 0 | 1,450 / 0 |
| 同一历史谷价估算，美元 | 18.7951 | 22.0582 | 10.0147 | 4.9637 |

按任务配对，只看“基线严格通过、SP 首轮未严格通过”的题。Codex 有 19 题，其中 15 题执行更久，逐题耗时比中位数为 **1.62 倍**；两端用量完整的 17 题中，16 题 Codex 费用更低。DSH 有 21 题，其中 17 题执行更久，耗时比中位数 **1.60 倍**；两端用量完整的 18 题全部费用更低且请求更少。只看当版新跑的 C/MS，对于两套基线分别都有 10 道这样的题，其中 Codex 8 题、DSH 7 题执行更久。这是选定获胜子集的描述，不能据此预测给任意一道题延长时间的效果。[逐题配对及覆盖](evidence/sp-tradeoff-evidence.json)

为什么“更慢”仍可能“更便宜”？按同一历史谷价，SP 首轮未命中输入为 17.776M，约 **$11.73**；Codex 为 1.831M，约 **$1.21**；DSH 为 1.232M，约 **$0.81**。SP 首轮可计量 DeepSeek 费用中根执行约 $12.81、分支 $3.27、投机请求 $2.72。SP 的并发缩短了许多题的墙钟时间，时间与 token 分开计量。不同系统的模型前缀和请求组织也不同，费用总差不能归因于以下任一机制。[请求与费率明细](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md)

## 2. Codex 的两项机制

### 2.1 长验证可以交回控制权，稍后读取同一个进程

`exec_command` 可以在子进程仍运行时返回会话 ID，由 `write_stdin` 继续读取，直到实际退出。59 题中有 **9 个独立进程、覆盖 6 题**返回会话 ID；其中 **8 个进程、覆盖 5 题**收到后续共 **15 次**续读。进程与续读按会话 ID 配对，持续等待同一进程只计一个。SP 的受控 Shell 默认以前台方式等待，有超时与进程清理、截断长输出和完整日志落盘。本轮首轮 66 个截断回执、覆盖 32 题，66 个都有完整日志路径。SP 可以找回已产出的长输出，当前公开工具契约里未见能把同一个仍在运行的验证进程交回模型后再接回的接口。[Codex 启动](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L404) · [Codex 续读](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/handlers/unified_exec/write_stdin.rs#L89) · [SP Shell](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py#L20) · [SP 归档统计](evidence/sp-tradeoff-evidence.json)

**MS41 显示了价值，也显示了成本。** Codex 先运行候选实现，随后自行编写随机路径采样和独立计票逻辑。第一次长模拟经过多轮等待后中止，第 26–27 步用较小的模拟取得近似结果和正常退出回执。它没有把产出与候选值做带容差的自动断言，轨迹也没有出现“对拍找到业务反例 → 修复生产算法”的链条。SP 在同题两个分支做过组件检查，根也执行了公开检查；其 5/11 与 Codex 的 11/11 提示值得比较两种验证的覆盖面。反向案例 MS23 更重要：Codex 调用 5 次续读后为 0/10、执行 1,223.58 秒；SP 首轮 10/10、209.65 秒。续读提供了完成检查的机会，空轮询也会消耗时间和模型轮次。[Codex 原生回执索引](evidence/codex-followup-evidence.json) · [SP MS41 原始 trace](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl) · [逐题分数](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

**给 SP 的取舍。** 优先为有明确退出条件的测试或构建提供受管句柄，将退出码、输出偏移和被测工作区版本绑定。仅在同一冻结副本上并发执行只读检查，测量真实重叠秒数。潜在收益是少重复启动长检查、发现公开用例外的边界错误；潜在代价是额外 CPU、轮询 token、等待时间，以及检查期间工作区变化后结果失效。只有同时记录首次产出、最终退出、是否发现新失败和修复后得分，才能区分“验证有用”和“等得久”。

### 2.2 长会话用语义摘要交接给下一段执行

9/59 道 Codex 题的原生 rollout 记录了 **10 次** `compacted`，均来自历史 MP 题。每次都有非空摘要和替换历史，之后均有真实 Shell 调用，4 个窗口之后还有补丁操作。MP26 的摘要 4,708 字符，随后出现 35 次执行及 3 次补丁，最终 26/26 严格通过；SP 首轮及采用重放策略后均 25/26。反例 MP14 压缩后仍有 34 次执行及 3 次补丁，Codex 最终 9/13、未严格通过，SP 通过重放取得 13/13。9 题中 Codex 严格通过 6 题，采用重放策略的 SP 为 5 题。压缩后的工具数描述后续工作，不能解释究竟哪一个改动带来得分。[Codex 历史替换](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/compact.rs#L414) · [逐题压缩窗口索引](evidence/codex-followup-evidence.json)

**SP 已有实际生效的压缩。** 它可把早期消息压成确定性的证据记录，保留最近的完整工具交互，并维持原始历史；另有叙述和握手摘要。在首轮根模型返回的路由元数据中，3 题共 **50 次**标明采用了压缩请求视图（MP12、MP22、MP26），独立重放中 1 题有 **32 次**。SP 的单位是“使用该视图的模型响应”，Codex 的单位是“会话历史替换事件”，两种次数不能比较压缩频率。可借鉴之处是给长根任务做一次可持久沿用的语义交接，明确保留已排除假设、尚未通过的用例和下一条验证命令，再以持久证据校验摘要。风险是漏掉约束、摘要增加模型开销、替换前缀可能影响缓存；收益应看后续输入规模、重复探查和跨窗口错误，而非压缩触发数。[SP 请求视图实现](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/context_compaction.py#L156) · [SP 叙述摘要](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/run_case_live.py#L515) · [SP 逐题事件](evidence/sp-tradeoff-evidence.json)

## 3. DSH 的两项机制

### 3.1 原生编辑会拒绝当前会话未观察或已过期的文件版本

DSH 按会话和文件跟踪最后一次观察的版本。59 题共 2,373 次工具调用中，有 **91 次因未读先写被拒，1 次因读后版本变化被拒**，覆盖 41 题。按每条拒绝向后对齐同路径，88/92 次能看到成功重读与随后成功修改，覆盖 40 题；两条拒绝可以对应同一次恢复。88 次配对中，**79 次修改载荷和先前完全相同，9 次发生变化，涉及 8 题**。唯一可确认的旧版本冲突发生在 C033 的自编测试文件。第 275 个非空事件拒绝旧版本 edit，第 279 个事件重读，第 283 个事件扩大旧片段匹配范围后成功。该题 DSH 严格通过，但这条链条验证的是测试文件的修改安全性，不能给它记上一道算法修复的功劳。[DSH 文件观察策略](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/fs-observation-policy/src/index.ts#L63) · [DSH 原生写入](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/write.ts#L117) · [脱敏逐事件配对](evidence/dsh-followup-evidence.json)

SP 已要求显式声明是否覆盖，也有文件哈希、重复内容和分支交付检查。当前普通整文件覆盖路径未见 DSH 这种“调用会话上次读到的文件版本”检查。此前局部编辑方案已提出传递预期哈希；新增建议是将它用于**分支合并后的已有文件覆盖**，让写保护在真正可能出现多个写入者时起作用。它可减少过期覆盖、改善完整性与组合验收；对本轮多数 DSH 拒绝，直接可见的代价却是多一次读取和重试。部署时应看实际版本冲突数、内容改变数、陈旧覆盖事故、写入到复验的耗时，以及正常串行任务多花的 token。[SP 普通写入](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L151) · [SP 覆盖参数](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L395)

<a id="source-line-56"></a>
### 3.2 整题交付清单可以跨普通业务轮保留

DSH 的 `todo_write` 将完整清单替换并投影到当前会话。**33/59 题使用、总计 88 次**，31 题更新至少两次。27 题从仍有开放事项更新到全部完成，其中 **17 题严格通过，10 题仍未严格通过**。MS41 有四个清单事项并最终严格通过；C007、C017 同样全部勾选，仍未严格通过。源码和 trace 一致支持“待办状态可被持续维护”，验证成功仍须靠实际运行的回执。Codex 的 `update_plan` 在本批有 3 道题各请求一次，三次均返回不支持，因此没有把这个工具作为 Codex 的有效优势。[DSH 清单工具及会话投影](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/todo/tool-todo/src/index.ts#L123) · [DSH 逐题统计](evidence/dsh-followup-evidence.json) · [Codex 回执](evidence/codex-followup-evidence.json)

使用清单的 33 题严格通过 22 题，其他 26 题通过 14 题。对应完整 E2E 中位数为 **563.8 / 294.2 秒**，总 token 中位数 **843,590 / 319,589**。两组任务构成差异很大：MP 题 21/25 使用清单，C 题仅 7/20 使用；仅看 C 题，使用组严格通过 3/7，其他为 7/13。直接拿全样本两组之差估算清单效果会误判。SP 的调度前沿已保存就绪、阻塞和完成项，也有根集成提醒。值得试的是让根在日常业务轮保留**少量跨分支的公开交付要求**，并用当前版本上的可执行回执关闭事项。预期代价是重复写清单、占用上下文、与握手重复，以及模型误勾后过早交付。优先复用现有状态，先观察遗漏的接口或产物是否减少。[SP 前沿工具](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L664) · [题族分层和原生回执](evidence/dsh-followup-evidence.json)

## 4. 一个比“多做几次验证”更具体的发现：MS41 如何检查自己的答案

三套系统在 MS41 **都通过公开检查，也都自行编写了测试**。最值得 SP 单独试验的行为，是给同一个可调用组件喂入许多不同输入，逐一同独立计算的期望结果比对。DSH 在这题的原生 trace 留下了这样一条可复核的执行链。这是模型利用 Shell 实现的验证策略，SP 已有执行它所需的工具。它与上文的运行时功能应分别消融。

| MS41 | 做了什么验证 | A 检查；登记检查；Reward | 执行阶段；已计量 DeepSeek 估算 |
|---|---|---|---|
| SP 首轮 | 两个分支各写组件测试，根运行公开检查及自检。自编参考函数在环图上先递归溢出，改写辅助算法后五项测试通过。归档主要覆盖固定样例与公开数据，未见大量随机输入逐项对照候选实现。 | 5/11；7/15；0.7/3 | 374.10 秒；$0.31002 |
| Codex | 第 26 步用另一种图路径采样方法估计结果，每个设定采样 40,000 次，第 27 步读取输出。计票停止条件与生产实现相近，未见带误差阈值的自动对比。 | 11/11；15/15；3/3 | 811.79 秒；$0.11121 |
| DSH | 首轮第 13–14 步公开检查已过。第 17 步参考计算报不一致，第 18 步手算得到 13/3，定位了参考计算自身的条件成本错误。修好参考实现和随机样例生成器后，第 20 步固定种子比较候选与参考的完整输出，**500 例、0 差异**。 | 11/11；15/15；3/3 | 529.95 秒；$0.10782 |

真正的区别是**用例覆盖和判定方法的独立程度**。SP 的反例恰好说明“再写一个参考函数”本身也做过；DSH 的 500 例给出了超出固定样例的交叉检查，但实际抓到并修正的是参考程序。三个系统都没有足够证据把本题的正式得分差归因于某次检查修复了隐藏错误。SP 正式失败项涉及环、自环、组合配置和条件成本等，这些标签只用于事后解释。可以在公开约束足够定义期望值的任务里，让验证分支从题面独立导出小规模参考解，打印可复现的最小反例。须同时记录“实现错”“参考解错”“输入生成器错”，否则更多测试可能只增加 CPU、token 和验证耗时。[SP 自编测试与回执，第 1364–1443 行起](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl#L1364) · [两套基线原试次路径索引](evidence/baseline-trace-metrics.json) · [正式逐题分数](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

**从交付代码能定位两处具体失配。**

1. 题面规定每轮先抽一次环境（profile），同一轮投票均共享它。SP 提交的整合代码第 53–62 行先求出各环境的加权单票分布，再从这个混合分布计算整轮结果。举个最小例子：两种环境等概率，其中一种每票必投甲，另一种每票必投乙。按题面，两张票必定相同；若每票重新抽一次，两张票不同的概率就成了 50%。两种算法可以有相同的单票正确率，却给出不同的整轮结果。归档失败的 `A/common-profile` 和 `A/two-profile-mix` 与这一实现差异吻合。这也是验证分支适合独立构造的小反例。[公开题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS41/instruction.md) · [SP 写入整合代码的回执所在步骤](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl#L1178)
2. SP 吸收概率组件在进入中间状态时，把这条边的加权成本全额加给每一种可能的最终答案。按题面，分配给某个答案的成本质量还要乘以从该状态最终到达该答案的概率。若后续有两个等概率答案，各自只能分到该入口成本的一半。这与正式失败项 `A/cost-follows-answer` 一致。两处失配能解释特定语义，其他未过项仍按原始回执保留。[SP 写入组件代码的步骤](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl#L414) · [逐题失败项](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

## 5. 怎么验证每个改动究竟换来了什么

| 可独立开关的改动 | 希望改善的结果 | 可能付出的代价 | 能区分两者的测量 |
|---|---|---|---|
| 受管验证进程 | 长验证完成、发现新反例，最终改善 A 和严格通过 | 空轮询、CPU 竞争、校验变旧、长尾 E2E | 实际退出码、无需重启完成数、新反例→修复→重新评分、重叠秒、轮询 token |
| 合并后写入校验观察版本 | 减少过期覆盖和集成回归，提高严格通过 | 更多读写轮次、等待和输入 token | 真正版本冲突与仅未读分别计数、重试载荷变化、回归与返修时间 |
| 有回执的根交付清单 | 避免漏入口、漏产物、漏做跨组件验证，提高严格通过 | 状态维护轮次、重复提示、自报完成失真 | 关闭项与同版本回执匹配率、B/D/P 通过、公开过而严格未过的题数 |
| 长会话语义交接 | 保留失败线索并继续返修，降低重复探查 | 摘要遗漏、额外请求、缓存命中下降 | 同一历史窗口后重复查找次数、约束保真、输入未命中 token、严格通过和尾部 E2E |
| 按公开规格生成输入并同独立参考计算对照 | 扩大边界组合覆盖，改善 A 和严格通过 | 参考解与实现共享错误、测试自身出错、CPU 与验证时间增加 | 有效反例数及归因、候选实现实际修复数、用例覆盖、验证分支占时与成本 |

**建议先配对试受管验证与合并后写保护，分别开关。** 选 MS41 检查复杂验证能否收尾，C033 检查共享文件版本，MS23 保留为 SP 原本成功的回归对照；这些题只验证机制，不能当作总体收益样本。把两组的增量都叠加在同一版 SP、同一根校验流程上，冻结题面、DeepSeek 配置、辅助模型、预算、CPU 配额和并发。对照顺序随机化，以任务×重复配对，首轮对首轮。最终在未按胜负选出的题上复验，同时报告严格通过的双向变化数、A 检查通过数、新版 Reward、完整 E2E 中位数及尾部、父子与辅助模型的 token 和可计量成本。超时、缺用量和缺外层计时各自保留。这样可以检验“保护了整题交付，但用更多时间”以及“增加流程却没有改善评分”两种结果。

## 6. 复核范围与资料

- 三个系统各 59 个首轮题位，另读 SP 的 9 次重放；其中 6 题采用重放成绩，重放成本包含全部 9 次。基线 30 个 C/MS 为新跑，4 个 N 沿用原运行，25 个 MP 使用已选历史产物离线复评，耗时和用量回连原试次。Codex 本轮 59 个原生会话的 CLI 版本均为 0.164.0。DSH 以原生工具调用 ID 关联回执，Codex 以原生 rollout、轨迹步及会话 ID 关联。源码定位对应本机复现快照；SP 归档的部分挂载覆盖文件与当前树哈希不同，历史是否触发以 trace 为准。[基线与 SP 总账](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md) · [SP 固定源码提交](https://github.com/xi474/SemanticParallel/tree/109a65444b3d4884fe92ec9e1c543b85df34e95d)
- 逐题用工作区 `delivery-bonus-50-v1` 复核了 4 个统计口径共 236 条分数。完整性为真时，登记难度权重乘以（半数核心检查通过率 + 半数严格通过指示量）。核心分母含登记的 A、B、D 和一次 P；表首行只统计 A。完整性失败为零，缺整份评分按未知处理。执行时间仅作近似同边界比较，SP 完整 E2E 未记录；费用仅按已计量 DeepSeek 请求统一历史谷价估算，SP 的 Qwen 预测/摘要、宿主 CPU、评分及缺用量未折款。[评分政策](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [逐题实现](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)
- 可复验材料：[Codex 审计结构化审计数据](evidence/codex-followup-evidence.json) 与 [结果](evidence/codex-followup-evidence.json)，[DSH 审计结构化审计数据](evidence/dsh-followup-evidence.json) 与 [结果](evidence/dsh-followup-evidence.json)，[SP 与配对指标结构化审计数据](evidence/sp-tradeoff-evidence.json) 与 [结果](evidence/sp-tradeoff-evidence.json)。前两者读取本机已有的原生试次归档；第三份只读本目录的评分与 SP 快照。全部统计离线完成。
