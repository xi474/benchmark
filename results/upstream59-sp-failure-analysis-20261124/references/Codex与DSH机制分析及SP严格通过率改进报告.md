# 从 Codex、DSH 的执行轨迹到 SemanticParallel 的严格通过率改进

**团队评审稿 · 2026 年 11 月 24 日补充错误发现机制**<br>
数据为 Upstream59 v2.1.0 的 59 道同题对照，主模型为 DeepSeek V4 Pro 普通模式。SP 指自研系统 SemanticParallel，早期归档使用 SemServe 名称。本文前半部分是已完成的源码与运行轨迹分析，后半部分是据此提出的开发和实验安排。

## 一、Codex 和 DSH 有哪些机制是 SP 当前缺少的

**以这次实际运行的版本为界，源码和工具轨迹能确认三项接口差距。** 下表的“缺少”具体到模型可以调用的操作。它既不等于 SP 做不到相同业务操作，也不能单凭调用次数估计某项接口对通过率的贡献。

| 对照系统已有且用过 | SP 当时具体缺什么 | 对严格通过率的证据 |
|---|---|---|
| **Codex 的 `apply_patch`、DSH 的 `edit`** 可对已有文件提交局部补丁或定向替换。归档识别到 465 次和 60 次调用 | SP 可由 Shell 改几行，也能整文件或分块写入；工具注册里缺少模型可直接提交上下文补丁或唯一旧片段替换、并收到匹配结果的操作 | MS11、C068 都出现 Codex 修改生产代码后，同一个原先失败的公开检查转为通过。这个顺序把返修和结果联系起来；把界面换成 Shell 能否取得同样效果，仍需消融。[工具轨迹](evidence/strict-trace-audit.json) |
| **DSH 修改前校验本会话读取的文件版本**。遇到未读文件或版本已变，可重读后再改 | SP 有分块偏移、产物哈希和终检版本核对；普通覆盖写入缺少以**该调用者上次读到的版本**为前提的保护 | 92 次拒绝中，91 次是未读先写，仅 1 次证实版本真的已变；88 次随后同路径重读并成功修改。对根整合分支修改有保护价值，本批没有证据说明 SP 因这项缺失少过几题。[DSH 读写配对](evidence/dsh-followup-evidence.json) |
| **Codex 能用会话 ID 续读同一进程；DSH 能按作业 ID 查询和取消后台作业** | SP 的前台 Shell 能等退出、保存长日志；当前注册接口缺少可交回模型并在后续轮次续接同一活进程的句柄 | Codex 在 5 题续接 8 个进程、共 15 次。DSH 在 MS23 查询仍运行的枚举作业并请求取消。尚未找到仅因 SP 缺句柄而丢失严格通过的同题反例。[Codex 进程配对](evidence/codex-followup-evidence.json) |

**最能解释分差的行为是根 Agent 如何验证和修正整题。** 首轮 SP 严格通过 25 道，DSH 36 道，Codex 38 道。SP 未过而对照至少一家通过的 26 道中，18 道 SP 已过公开样例。另有 C069 这样的独立问题：控制协议连续失败时，根无法回到实现。这两类问题需要不同改动。[同题对照](evidence/strict-outcome-paths.json)

**开发优先级。** 在首次得到可运行的整题后，先依据公开契约独立算出组合输入的期望，调用真实入口，保留失败样例并在修改后原样重验。SP 已有自检、Shell 和根集成，主要要补的是跨组件用例的覆盖以及反例及时返回。DSH 在 MS41 自主写过独立参考算法；强制隔离验证者及预先封存期望，是为 SP 提出的可测试设计，两套对照均无证据表明默认强制执行。局部编辑可作为第二个独立开关。C069 的协议降级单独修复，写版本保护和进程续接分别评估。

## 二、要改善的是哪部分成绩

| 59 题结果 | SP 首轮 | SP 含公开失败重放 | Codex | DSH |
|---|---:|---:|---:|---:|
| 核心转换 API 通过数 | 633/803（78.83%） | 669/803（83.31%） | 683/803（85.06%） | 633/803（78.83%） |
| 整题严格通过 | 25/59 | 28/59 | 38/59 | 36/59 |
| Reward，满分 138 | 78.469237 | 85.361619 | 97.306571 | 91.162733 |
| 其中，严格通过加分 | 28.5 | 32.0 | 43.0 | 40.5 |
| 执行阶段中位数，秒 | 247.95 | 317.12 | 716.68 | 426.04 |
| 完整 Harbor E2E 中位数，秒 | 未知 | 未知 | 749.57 | 458.67 |
| 已计量输入 / 输出 token，百万 | 179.929 / 1.765 | 209.898 / 2.037 | 102.672 / 3.327 | 45.773 / 1.601 |
| 已计量输入缓存命中率 | 90.12% | 89.99% | 98.22% | 97.31% |
| DeepSeek 费用，统一历史谷价估算 | $18.7951 | $22.0582 | $10.0147 | $4.9637 |

**同样通过 633 个 API 用例，DSH 比 SP 首轮多严格通过 11 道题。** 两者 12.693496 分的 Reward 差距中，12 分来自严格通过加分；Codex 领先 SP 的 18.837334 分中，14.5 分来自这项加分。逐题看，SP 有 34 题未严格通过，每题都至少缺一项核心 API。其中 **25 题已经通过公开检查**，8 题仅有 API 缺口，17 题还缺其他登记检查。5 题只差 1 项，2 题只差 2 项；这 7 题合计漏掉的 9 项全是 API 检查。公开失败才触发的重放自然覆盖不到它们。[59 题逐题分数与失败项](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json) · [Reward 分项复核](evidence/sp-tradeoff-evidence.json)

**改进还要保住速度。** SP 首轮在 51/59 题上的执行阶段短于 Codex，在 46/59 题上短于 DSH；其已计量费用却更高。SP 首轮有 17.776M 未命中缓存的输入 token，Codex 为 1.831M，DSH 为 1.232M。每增加一个验证分支，都要同时衡量它修好了几道题、延长了多少墙钟时间、增加了多少未命中输入。[用量与费用明细](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md)

### 同样的用例总分，怎样变成不同的整题通过率

按每题正式 A 类核心转换用例是否全部通过，将 59 道题各计一次。下表是首轮冻结成绩。完整性失败时评分规则给零，这些题仍保留在“正式为零”列。

| 首轮，59 题 | 核心 API 全过 | 过一部分 | 正式为零 | 整题严格通过 |
|---|---:|---:|---:|---:|
| SP | 25 | 30 | 4 | 25（42.4%） |
| DSH | 37 | 12 | 10 | 36（61.0%） |
| Codex | 39 | 14 | 6 | 38（64.4%） |

SP 所有 API 全过的题也都严格通过。DSH 比 SP 多 12 道 API 全过的题，其中 MP12 还缺 `io/commit`，所以严格通过净多 11 道。Codex 比 SP 多 14 道 API 全过的题，其中 MP01 缺 `output/final_report`，净多 13 道。**即便修好所有纯交付问题，只要这 34 道题的功能行为保持原样，SP 首轮的严格通过数仍是 25。** 修复一个根因可能同时改善多个入口和产物。[逐题分类与正式分母](evidence/strict-outcome-paths.json) · [登记失败项](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

### 34 道失分题最后走到了哪里

以下分组只取每题根会话**最后一份** `output_guard_checks.jsonl` 回执，与正式评分交叉核对。“同版本”表示最终公开检查确认候选版本匹配；“有限自测”是在 Agent 可见范围内运行的一小组用例。

| SP 首轮最后留下的运行时证据 | 题数 | 正式严格通过 | 正式未严格通过 | 失分题中 Codex 或 DSH 至少一家严格通过 |
|---|---:|---:|---:|---:|
| 有限自测通过，最终同版本公开检查也通过 | 37 | 18 | **19** | 12 |
| 最近的公开检查通过，缺最终同版本通过回执 | 13 | 7 | **6** | 6 |
| 没有归档根会话的这类检查回执 | 9 | 0 | **9** | 8 |

**19/34 道失分题已经完成同版本检查。** 这 19 题中只有 4 题差一项登记检查，其余 15 题差 2–13 项。修复过期回执或再跑一遍相同自测，都无法识别这类遗漏。另有 9 题连根检查回执都没有，适合单独排查执行在哪一步停住；它们仍有正式评分，分支或 Shell 也可能做过检查。7 题记录自检预算耗尽，其中 5 题最终严格通过。这几类信号回答的是不同问题，不能把超时次数直接用作失分数。[逐题运行终态与回执](evidence/strict-outcome-paths.json) · [自检与工具事件](evidence/strict-trace-audit.json)

### 完整性异常会怎样影响分差

SP 有 5 题严格通过且 Codex、DSH 都未严格通过。**其中可直接比较三方业务行为的是 C007、C017**，三方完整性均通过。C056、MS12、MS23 的两套基线均未通过完整性检查。进一步对照六套基线的归档，三题的 `contract.json` 分别指向 C055、MS11、MS14。C056 和 MS12 的原始评分还列出部分受保护文件，但在最终归档中抽查的对应文件与冻结文件哈希相同。归档和评分发生在不同环节，现有材料无法判定合同在哪一环节串用，亦不能判定由哪个 Agent 写入。三题均保留正式零分，不能据零分还原业务函数表现。[合同身份与归档校验](evidence/contract-identity-audit.json)

作为敏感性核对，在三方完整性都通过的同一组 **52 题**上，SP、DSH、Codex 分别严格通过 **22、36、38 题**。若逐对比较业务用例，SP 对 DSH 为 **581/734 对 633/734**；SP 对 Codex 为 **582/744 对 683/744**。两组分母不同，是因为 DSH 有 7 格、Codex 有 6 格完整性失败。这是按结果筛选的诊断子集，正式排名仍使用完整 59 题。另从严格结果分歧入手，在“SP 未过、至少一家对照过”的 26 题中，18 题 SP 已过公开样例，4 题公开未过但 API 部分有分，4 题公开未过且 API 为零。优先看第一类的组合规则，可以直接研究影响系统差距的失败。[含逐题完整性标志的复核表](evidence/strict-outcome-paths.json)

## 三、Codex 和 DSH 怎样让错误暴露

**运行时给模型一个验证习惯，具体怎样把缺陷触发出来由模型按题决定。** 在 Codex 的 59 份原生会话中，59 份都记录了先对改动做最具体的检查、再扩大测试范围的基础指令。在 DSH 的 59 份原生会话中，59 份都记录了要求检查每次 Bash 退出码、失败先调查的系统提示。一个偏重“下一步测哪一层”，一个偏重“已经失败的信号能否被注意到”。两者都可以自己选择输入、写参考程序、调用真实业务入口。没有证据表明这 59 题在解题阶段拿到了隐藏评分答案。[逐题原生提示与检查记录](evidence/error-exposure-evidence.json) · [Codex 验证指令](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/protocol/src/prompts/base_instructions/default.md#L149) · [DSH Bash 提示注册](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L249)

| 主动改变了什么 | 第一处可核对的信号 | 这条轨迹支持什么结论 |
|---|---|---|
| **DSH · MS02，换成会让两条规则相互冲突的最小输入。** 两个主题都只能选同一篇论文，但论文不得复用。按公开题意，这个输入合法，完整分配不存在，应返回 `null` | 组件和整题公开样例先通过。DSH 随后直接调用 `solution.transform`，在递归代码中得到 `TypeError`，退出码 1。工具消息的外层状态仍是 `completed`，正文保留了异常位置和退出码。修改生产代码后，同一输入返回 `None` | 这是公开样例之外的真缺陷。判定标准能由题面直接推出。DSH 正式 API 9/9；SP 的两项正式失分是平局与并行证据，无法把这两分归给该探针。[公开题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS02/instruction.md) · [DSH 原生记录，stream 第 75–99 行](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip) |
| **Codex · MS30，保留同一题，换真实运行入口。** 单跑公开检查后，接着执行组件写产物、合并及整题流程 | 第 24 步公开检查通过；第 25 步组件在计算输入指纹时遇到无法 JSON 序列化的 `Fraction`。实现曾把中间数值写回输入记录。第 26 步改为单独存放中间值，第 27 步重跑同一流程通过，第 28 步另外检查输入保持不变和干净目标构建 | 纯函数返回可用，仍可能在落盘和交付时失败。正式评分另因完整性失败记零；此处证明发现并修复了具体缺陷。[Codex 原生记录，trajectory 第 24–28 步](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS30.zip) |
| **Codex · C055，将原本分开测试的规则组合起来。** 两个组件及公开检查都通过后，把密文放入可信模板的引用路径，再分别保留标签、提供钥匙、移除钥匙 | 第 11 步打印了 `hi-[sealed]`、`hi-unlocked` 和缺钥匙的 `sealed` 状态。相同规则在 SP 中只测了直接输出密文，模板递归路径返回了错误值 | Codex 这次探查时结果已经正确，证明它覆盖了区分两套实现的场景，不能计作“抓到后修复”。正式 API 为 Codex 9/9、SP 8/9。[Codex 原生记录，第 9、11 步](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C055.zip) · [SP 自测输入](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl#L1266) |

按可识别的检查命令，Codex 在 **59/59** 题做过检查，**54/59** 题至少有两次；DSH 分别为 **54/59、51/59**。这里统计命令回执，内联 Python 探针可能归为普通 Shell，一条命令也可能串接多项检查。DSH 的 157 次已识别检查中，119 次未能从该汇总格式可靠判定通过或失败，故不依据汇总的失败次数比较谁发现的业务错误更多。[统计及逐题分母](evidence/error-exposure-evidence.json) · [命令识别口径](evidence/strict-trace-audit.json)

### 独立算一个期望，再看不一致来自哪一边

MS41 要求一整轮投票共享同一个随机环境。设环境甲、乙等概率，甲环境每票必投甲，乙环境每票必投乙。按题面，两张票一定相同。SP 的整合代码先平均两种环境的**单票**分布，再用这个分布计算整轮投票，得到两票有一半概率不同。单票分布正确，跨票关系却丢失。另一处失配发生在成本计算：程序把进入中间状态的边成本全额计入每种可能的最终答案，题意要求按后续到达各答案的概率分摊。[MS41 公开题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS41/instruction.md) · [SP 整合代码的原始步骤](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl#L1178) · [组件代码的原始步骤](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS41/dynamic_v7/trace.jsonl#L414)

| 系统 | 公开检查通过后或自检中实际做过的事 | 正式结果 | 执行阶段 / 已计量估算 |
|---|---|---|---|
| SP 首轮 | 两个业务分支写组件测试，根做公开检查和自检。自写参考函数曾在环图上递归溢出，修正测试后五项通过；用例主要来自固定样例与公开数据 | API 5/11，登记检查 7/15，Reward 0.7/3 | 374.10 秒 / $0.31002 |
| Codex | 用另一种图路径采样方法复核，每个设定采样 40,000 次并打印近似结果。计票停止规则与生产实现相近，轨迹未显示带容差的自动断言 | API 11/11，登记检查 15/15，Reward 3/3 | 811.79 秒 / $0.11121 |
| DSH | 写独立参考算法；第一次发现差异后手算，定位到参考算法自身出错。修正参考计算和生成器后，固定种子，逐项比较 500 个小输入的完整输出，最终 0 个差异 | API 11/11，登记检查 15/15，Reward 3/3 | 529.95 秒 / $0.10782 |

**这个案例支持“独立计算和组合输入值得测试”。** 三家都写了测试，差别在于测试覆盖了哪些语义、期望值从哪里来。DSH 的 500 例是模型在该题使用 Shell 实施的策略；源码和 trace 均不足以认定 DSH 默认每题强制这样做。轨迹也未显示是这次比较修好了生产代码。SP 因此需要同时记录“候选实现被修正”和“参考程序被修正”。[原试次索引](evidence/baseline-trace-metrics.json) · [本题逐项分数](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

### 一个被自测漏掉的功能组合

**C055 是 SP 差一个核心 API 就能整题过关的实例。** 题里有一个保留值，在最终输出中应显示为 `[sealed]`。SP 只在顶层直接输出它时做了遮蔽。模板经别名间接引用同一值，递归函数返回了原标识。四个自测全部通过，其中检验了顶层遮蔽，漏掉了“模板＋别名＋保留值”的组合。DSH 将遮蔽规则放入共享递归函数，两条调用路径都经过它。最终 SP 为 **8/9 API、12/13 登记检查、Reward 0.923077/2**，Codex 与 DSH 均为 **9/9、13/13、2/2**。这说明同一条遮蔽规则在两个入口之间丢失，自测也遗漏了那条路径。把遮蔽放进共享函数是 DSH 在本题的实现决定，不能当成 DSH 运行时自动验证该规则的机制。[SP 整合实现](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl#L1218) · [SP 自测代码](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl#L1266) · [基线原试次索引](evidence/baseline-trace-metrics.json)

### 两次直接观察到的业务返修

**MS11，组件各自通过，组合起来却错了。** Codex 第 17 步运行两个组件检查，两者都通过。第 18 步运行整题 `public_check.py`，退出码为 1。它用实际入口重建输出并核对，随后两次局部修改生产文件 `integration.py`，按学生 ID 对齐分数、映射和买家向量。第 22 步原样重跑整题公开检查，退出码为 0，之后重新生成组件产物并执行合并。正式核心 API 为 **10/10**。SP 首轮正式 **1/10**，独立重放也是 **1/10**。SP 根在首轮确实运行了整题公开检查，且输出已经显示买家向量顺序不对；没有根 Output Guard 完成回执，不能据此说它没检查。根随后在状态报告里写下要修排序并重跑原检查，但反复打印相同向量。运行时提醒它修改实现，轨迹中仍未见对生产文件的第二次写入，最终因重复操作中止。这道题把差别定位在**拿到反例后，是否将修复写回实现并复验**。没有证据把九项失分逐项归给这一个排序错误。[逐步事件索引](evidence/strict-trace-audit.json) · [SP 打印期望与实际](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7/trace.jsonl#L930) · [SP 提示修复后再次拒绝重复操作](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7/trace.jsonl#L1266)

**DSH 的 MS11 还显示，第一处修改不一定能修好。** 它最初已经通过公开样例，随后为 14×14 输入优化生产代码，引入动态规划回归。第一次改边界后原公开检查仍失败。接着它检查中间矩阵与配对，再次修改生产文件，原公开检查、与暴力参考解的对照、平局和性能用例均通过，正式 **10/10**。这是一次优化后的真实业务返修。原件可按试次索引定位，文件为 `MS11__4EcjotE/agent/dsh-stream.jsonl`，第 133–173 行；Codex 同题原件为 `MS11__uYq3NxG/agent/trajectory.json`。[基线试次索引](evidence/baseline-trace-metrics.json)

**C068，修改的是生产逻辑，复验用的是原来的检查。** Codex 第 21 步公开检查失败，第 22 步打印实际与期望，第 23 步修改 `core.py`，查询结果的下标改为只对 `get` 事件计数。第 24 步同一公开检查和两个组件检查通过，随后重建产物，并在干净目标下核对程序入口的一致性，正式 **9/9**。SP 已经通过公开检查及有限自测，正式仍为 **8/9**。两条轨迹提供的是同一任务的不同执行路径；并无证据表明 SP 的最后一项失分也是上述下标错误。[逐步工具与退出状态](evidence/strict-trace-audit.json) · [正式逐项结果](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

**这类返修在多少道分歧题上出现过？** 单独选出某一基线严格通过而 SP 未通过的题，Codex 有 19 道，其中可从事件顺序确认“检查失败、随后编辑、再次检查”的有 5 道，为 MP02、MP19、C068、MS11、N17。DSH 有 21 道，其中能确认该顺序的有 3 道，为 MP15、MS11、MS41。两组有重叠。这个口径只识别工具顺序，不能自动判断修改的是测试还是业务；DSH 有些工具返回也只报告结束。上面两例另核了 Codex 原始修改内容及同一检查的退出码。MS41 中 DSH 实际修的是参考计算，不能并入修正业务代码的案例。[逐步事件](evidence/strict-trace-audit.json) · [首轮分歧题](evidence/strict-outcome-paths.json)

## 四、可借鉴机制的源码与使用证据

| 机制与出处 | 此次运行观察 | SP 的改动与取舍 |
|---|---|---|
| **针对局部修改并复验**。Codex `apply_patch`、DSH `edit` | 已识别 Codex 补丁 465 次、DSH 局部编辑 60 次。两套工具都能把修改或失败反馈给当前 Agent | 首版用 SP 现有工具在同一工作区返修。后续增加按文件版本与唯一旧片段匹配的局部编辑，测每次成功返修的写入量、token 和 E2E。[Codex 补丁](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/runtimes/apply_patch.rs#L181) · [DSH 编辑](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/tool-fs/src/edit.ts#L94) |
| **写入前核对已读版本**。DSH 文件观察策略 | 41 题出现 91 次未读先写拒绝、1 次读后版本变化拒绝。88 次拒绝能关联到同路径重读与成功修改，其中 79 次重发相同修改内容 | 优先保护根在分支合并后对已有文件的覆盖。把真正版本冲突与普通未读分开统计，同时计入额外读取和重试成本。[DSH 版本校验源码](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/fs/fs-observation-policy/src/index.ts#L63) · [逐题证据](evidence/dsh-followup-evidence.json) |
| **续接仍在运行的检查**。Codex `exec_command` / `write_stdin` | 6 题中有 9 个进程返回会话 ID；5 题实际续接了 8 个进程，共 15 次。MS23 中 Codex 续读 5 次；该题正式零分来自完整性门禁，无法据此评价续读对业务实现的影响 | SP 已能保存长输出。若验证反复因进程中断而重启，可增加受管句柄，绑定输出偏移、退出码、候选版本和截止时间。收益看完成的有效检查，成本看轮询、CPU 与长尾等待。[Codex 续读源码](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/tools/handlers/unified_exec/write_stdin.rs#L89) · [逐题证据](evidence/codex-followup-evidence.json) |
| **跨轮维护待办**。DSH `todo_write` | 33 题共调用 88 次；27 题把全部事项勾为完成，其中 17 题严格通过，10 题仍未严格通过。使用组的 E2E、token 中位数较高，题型构成也不同 | 复用 SP 现有分支状态，优先保留少量跨组件交付要求，每个完成项指向同版本可执行回执。只有观察到事项频繁遗失时再单独试验。Codex 本批 3 次 `update_plan` 均返回不支持。[DSH 会话清单](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/todo/tool-todo/src/index.ts#L123) · [DSH 证据](evidence/dsh-followup-evidence.json) · [Codex 证据](evidence/codex-followup-evidence.json) |
| **长会话用摘要交接**。Codex 根会话历史替换 | 历史 MP 题中 9 题共出现 10 次替换，之后均继续执行命令，4 个窗口后还有补丁。MP14 压缩后继续修改仍未严格通过，SP 重放严格通过 | SP 已有请求视图压缩、叙述摘要和握手记忆。可另测在交接摘要里保留失败输入、已排除解释和下次检查。记录重复探查、摘要遗漏、未命中缓存 token 与严格通过变化。[Codex 历史替换](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/core/src/compact.rs#L414) · [SP 现有压缩](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/context_compaction.py#L156) |

这些数字衡量工具是否被用过和使用后的可见行为。模型、提示、资源调度、预算及上下文组织都有系统级差异，现有 59 题不能把 Codex 或 DSH 的严格通过加分分摊给某一个工具。

**失败后能否回到业务操作，有一组清晰的对照。** C069 中 SP 等待合法的分工状态报告，这一阶段根只能提交 `report_frontier_state`。连续 123 次参数校验失败后，根仍未回到业务实现，首轮 API 0/9；同题 Codex、DSH 和 SP 独立重放均为 9/9。其余遇到状态报告拒绝的 7 题都恢复了业务调用。C069 一题就占首轮 135 次此类拒绝的 123 次，修复它很有价值，不能把它当成 34 道失分题共同的主因。对照侧，Codex 在 13 题出现 14 次工具被桥接层拒绝或不受支持，随后均恢复命令执行或局部修改，13 次就在下一工具步骤。DSH 的文件校验拒绝中有 88/92 次关联到同路径重读和修改。这三类拒绝成因不同，可比较的是模型何时重新拿到能推进任务的工具。SP 可为同一字段重复报错设置有界恢复，同时保留校验、错误记录和已产生产物。[SP 根工具开放条件](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/runtime.py#L4641) · [C069 轨迹](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/trace.jsonl) · [Codex 工具证据](evidence/codex-followup-evidence.json) · [DSH 重读与修改](evidence/dsh-followup-evidence.json)

## 五、SP 首版怎样实现

### 哪些能力已启用，哪些需要开发

下表以 59 题归档和本地 SP 提交 `109a654` 为界。“有原型”指在这份源码里能找到实现；历史是否使用取决于归档的模式选择和实际事件。

| 能力 | SP 的实际成熟度 | 这次打算补什么 |
|---|---|---|
| 独立推导期望、执行断言、发现差异后返修 | **主线已有。** `serial_p02` 明确要求，MS41 也确实写过参考计算。D1/D2 另有独立评审工作者、候选私有副本、失败归因和重放；59 题主线采用 `serial_p02` | **新增可审计的先后顺序。** D2 先接收测试脚本，在候选副本运行，再归档脚本哈希与结果。首版拟在无法访问候选的环境先算好并持久保存输入和期望，再允许另一执行器首次访问候选，记录两个时间点。[D2 实际提交与执行顺序](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d2.py#L108) |
| 根集成、返修和最终同版本复验 | **主线已有。** 合并后已有集成检查点，提交时重验并确认候选版本稳定 | 增加“首个可运行整题”触发点，提前把可复现反例送回根，并沿用原终检。[根检查点](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L815) · [最终版本核验](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L49) |
| 局部编辑、合并后写保护、长进程续接 | **有相关基础，当前实验工具注册中未见对应的三个原生接口。** Shell 可局部修改；工作区有分块偏移与交付哈希；前台命令可返回退出码并落盘长日志 | 分别新增精确替换接口、按调用会话上次读取版本校验普通写入、可返回给模型并续读的在途进程句柄。三项可独立测试，首轮语义验证可直接用现有 Shell。[工作区工具注册](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L776) · [Shell 执行与日志](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/shell.py#L153) |
| 跨轮待办与历史摘要 | **SP 已有调度前沿、握手摘要、叙述摘要和请求视图压缩。** | 可选增强是把交付事项绑定到同版本检查回执，并在长会话切换后保留待解反例。两者列入后续评估。 |

**已有基础。** 冻结的 C/MS 配置采用业务 fork 和 `serial_p02` 自检，自检时限 300 秒。现有提示已经要求从公开规则推导独立期望、运行真实断言、修复并复验。D1 原型能提取公开契约与接口签名并在候选副本执行测试，D2 已能分类失败、保留反例、重放同版本测试。整套启用 D2 还会带入至少 3 个评审组、至少 30 个用例、最多 3 个并行工作者及 600 秒时钟。首版只复用所需组件，才能检验“期望如何产生”本身的价值。[SP 冻结配置](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/experiment_plan.json) · [现有自检](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_live.py#L249) · [D1 执行器](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d1.py#L79) · [D2 失败裁决](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/visible_contract_check_d2.py#L172)

| 顺序 | 要实施的行为 | 可复核的完成证据 |
|---|---|---|
| 1. 准备参考 | 创建独立验证上下文，只提供任务启动时冻结的公开题面、接口签名与公开输入。排除父会话实现历史、摘要、已有输出及共享文件泄漏 | 记录实际发送的提示、工具清单和允许读取的文件摘要；能核对首次访问候选的时间 |
| 2. 封存期望 | 对一两条高风险规则，用手算、枚举或可验证不变量给出期望。生成输入时保留生成器与随机种子；参考算法先在一个可手算例子上校验 | 留存输入、期望、公开依据、参考程序及其哈希和封存时点。规格有歧义时，仅断言可确定的部分 |
| 3. 检查真实入口 | 在指定候选版本的临时副本调用公开业务入口，按封存规则比较完整输出或性质 | 对齐反例 ID、候选哈希、期望、实际、退出状态；保留最小可复现输入 |
| 4. 裁决与修复 | 根 Agent 分别处理实现错误、参考错误、输入错误、规格歧义和基础设施错误。确认实现错误后在正式工作区修改；修订参考则另存版本与理由 | 只有业务代码实际修改并通过**同一原反例**复验，才计为有效业务修复。相同版本、相同失败避免重复调用 |
| 5. 收尾 | 重建受影响产物，运行原公开检查、完整性检查和最终版本复验。已经变化的候选使旧回执失效 | 对齐最后一次有效回执与提交版本；官方隐藏评分只在 Agent 结束后执行。自编测试不计入正式分母 |

拟议初值为每题最多一个额外评审席位、最多 8 个确定性对照输入、最多两轮有实质改动的返修。C/MS 附加评审拟从原 300 秒自检预算内最多分配 90 秒，并为原收尾留足时间。其余题族先核对各自预算。若参考或生成器出错，可保留原件并做一次有公开依据的修订；仍无法裁决或评审超时则记录未知，转回原完成流程。公开检查、受保护文件完整性和最终提交仍由原规则裁定。这些上限是待离线验收的设计值。

**第二版与可靠性改动。** 首次形成可运行整题时，用独立快照检查并向原根返回差异，正式 `finish_task` 仍负责最终验收。另为 C069 型故障设置独立恢复路径：同一代状态报告反复违反同一字段约束时，保留证据和已有产物，恢复根的业务工具。C069 首轮 123 次参数拒绝后始终没有业务实现，因此这项修复解决的是“能否开始做题”；独立验证解决的是“实现能否正确交付”。两项使用独立开关，A/B 两臂共享相同的基础设施修复版本。[根集成入口](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/parallel_runtime_v2.py#L815) · [最终检查入口](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/output_guard_live.py#L16) · [C069 首轮原件](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/trace.jsonl)

## 六、怎样决定改进是否值得采用

**先断网验收。** 用脚本化模型响应和公开小题验证四件事：封存前无法取得候选信息；注入已知组合错误后能产生反例并在修后重放；参考解或生成器自身出错时能正确归类；并发变化、过期产物、评审超时、账本中断时能保留证据并回到原收尾流程。增加等价正确实现作为误报对照。冻结实际镜像、覆盖层、工具权限、计时和评分版本后再登记付费批次。

| 拟议阶段 | 配对方式 | 用途 |
|---|---|---|
| 诊断 24 次 | MP19、C055、MS41、MS11、C069、MS23；6 题 × 2 臂 × 2 次。先取 MS41、MS23 各一对做技术试点，计入 24 次 | 两臂评审席位、预算、时点和执行器相同。A 写期望时可见候选；B 先按公开信息封存，再接触候选。MS23 用于捕捉 SP 原已成功的题发生回退 |
| 冻结版本验证 48 次 | 另 12 题 × 已登记原版 SP / 冻结交付版 × 2 次，两臂均新跑。清单为 MP20、MP21、MP17、MP09、MP18、N11、C066、C062、C011、C067、MS14、MS30 | 评估实际替换版本的净收益。覆盖 MP、N、C、MS 四族；这批题已有历史成绩，只能称冻结后未用于本轮调参的评估题 |

两阶段拟全局最多四个 trial 并发，平衡同题配对的先后顺序。固定 DeepSeek V4 Pro 普通模式、辅助模型、父子共享预算、CPU、题包、并发和缓存策略。四次技术试点按隔离、计量和版本证据放行，答错也保留。首轮对首轮，公开失败重放单列；提前根反馈、长进程续接和版本写保护另行消融。**24 + 48 是待评审的 72 次计划，本报告没有启动试次。**

**采用标准。** 主指标为配对的严格通过净增，同时列“新增通过、发生回退、两者皆过、两者皆未过、缺评分”。每次新增通过追溯到实际反例、裁决、代码修订和同版本复验。并列 A 类 API 准确率、新版 Reward、完整 E2E 中位数及 P90、输入输出和缓存 token、父子及辅助模型的可计量费用。两次重复按题汇总，未知评分和未知用量分别披露。可在看验证结果前登记一条初始性能容忍度：同口径完整 E2E 中位数和已计量总费用各增长不超过 20%。20% 是供团队选择的阈值；若净增不稳定或原本做对的题集中回退，继续保留原默认。

## 数据与复核口径

- **评分。** 使用 `delivery-bonus-50-v1` 逐题核对。完整性通过时，Reward 为难度权重乘以 `0.5 × 登记核心通过数 / 冻结核心总数 + 0.5 × 严格通过指示量`。登记核心含 A（核心转换用例）、B（接口）、D（产物）及计一次的 P（公开执行）；API 一行只计 A。完整性失败记零，缺整份回执记未知。[评分规则](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [工作区逐题实现](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/workspace_reward.py)
- **试次与版本。** Codex 原生记录为 CLI 0.164.0。两套基线的 30 个 C/MS 为当版新跑，4 个 N 沿用历史运行，25 个 MP 使用选定历史产物离线复评，用量与耗时回连原试次。SP 重放了 9 题，6 题采用新成绩，重放列计入全部 9 次的可观测资源。SP 源码对照提交为 `109a654`，部分现有覆盖文件与归档挂载哈希不同，历史行为以 trace 为准。[基线发布矩阵](https://github.com/xi474/benchmark/tree/a82cdb3b0f14c0e1207f44c23ac4e2753cc30f28/results/upstream59-v21-deepseek-v4pro-20261121) · [SP 运行归档](https://github.com/xi474/benchmark/tree/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve) · [SP 源码快照](https://github.com/xi474/SemanticParallel/tree/109a65444b3d4884fe92ec9e1c543b85df34e95d)
- **时间与费用。** 历史 SP 只归档了含运行时收尾的执行阶段；Codex、DSH 另有从 Harbor 试次启动到评分收尾的完整 E2E。费用采用统一历史谷价，只覆盖有用量记录的 DeepSeek 请求。SP 首轮 4,361 条请求中有 14 条缺用量；含重放为 5,116 条中 15 条缺用量；Codex、DSH 分别为 2,137 和 1,450 条，缺用量均为零。Qwen 辅助推理、容器和评分未折款，历史实际账单未知。[用量与边界](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md) · [Codex 原生工具审计](evidence/codex-followup-evidence.json) · [DSH 原生工具审计](evidence/dsh-followup-evidence.json)
