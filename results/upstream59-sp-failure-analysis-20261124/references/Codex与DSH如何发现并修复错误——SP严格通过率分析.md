# Codex 与 DSH 如何发现并修复错误

**基于 Upstream59 的 SemanticParallel 严格通过率分析｜2026 年 11 月 24 日**

这份报告回答两个问题。第一，公开样例已经通过时，Codex 和 DeepSeek Harness（DSH）怎样发现仍然存在的错误？第二，已经看到错误时，它们怎样确认交付程序真的改对了？对照对象是自研系统 SemanticParallel（SP）。三个系统均使用 DeepSeek V4 Pro 普通模式。正文比较每题选定的首轮结果，SP 另行重放的成绩不混入主表。[逐题记录与版本口径](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

## 结论

**错误能否暴露，取决于测试能不能区分两种看似合理、实际行为不同的实现。** Codex 在 C055 把模板引用和密文遮蔽放进同一个输入，正好覆盖 SP 遗漏的路径。DSH 在 MS02 构造了一个按题意必然无解的小输入，第一次让此前通过公开样例的程序抛出异常。这两种探查，都可以从公开规则推导期望。[Codex C055](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C055.zip) · [DSH MS02](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip)

**错误能否改对，取决于诊断之后是否发生了可验证的业务代码变更。** MS11 是最清楚的同题对照。Codex 和 SP 都看到了整题输出中买家向量的顺序异常。Codex 修改整合代码，用原公开检查复验，再重建产物；SP 写下了正确的修复目标，却继续打印同一组中间结果，最终因重复操作中止。这道题值得借鉴的是从反例到实际交付的完整过程。[Codex MS11，第 17–23 步](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS11.zip) · [SP 打印期望与实际](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7/trace.jsonl#L930) · [SP 末次重复操作](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7/trace.jsonl#L1266)

## 一、严格通过率的差距出现在哪里

“核心 API”按冻结的业务转换用例逐项计数；“整题严格通过”按题计数，还要求满足该题其余登记验收条件。Reward 引用工作区 `delivery-bonus-50-v1` 的逐题结果：完整性通过时，按任务难度权重，将严格通过与登记核心检查通过比例各计 50%。主表中的 API 仅为 A 类转换用例，Reward 采用的登记核心还含其他验收项。[工作区评分规则](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/scoring/reward-policy-v1.0.json) · [正式指标](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

| 59 道首轮任务 | 核心 API 通过数 | API 全过的题数 | 整题严格通过 | Reward 总分（满分 138） |
|---|---:|---:|---:|---:|
| SP | 633/803 | 25/59 | 25/59（42.4%） | 78.469237 |
| DSH | 633/803 | 37/59 | 36/59（61.0%） | 91.162733 |
| Codex | 683/803 | 39/59 | 38/59（64.4%） | 97.306571 |

SP 和 DSH 通过了同样多的 API 用例，分布却不同：SP 有 30 题只通过部分 API，DSH 有 12 题。DSH 比 SP 多 12 道 API 全过的题，其中 1 道还缺交付检查，最终严格通过净多 11 道。完整性异常也不足以解释这个差距。在三方完整性都通过的同一组 52 题上，SP、DSH、Codex 分别严格通过 22、36、38 题。[首轮分布与完整性核对](evidence/strict-outcome-paths.json)

有两个分母尤其重要。**在 SP 未严格通过的 34 题中，有 19 题已经通过有限自测，最终同版本公开检查也通过。** 这说明相当一部分交付即使重跑相同检查，仍不会出现错误信号。另一个角度是只看系统结果有分歧的题：**SP 未过而 Codex 或 DSH 至少一家通过的 26 题中，18 题的 SP 已通过公开样例。** 两组题有重叠，不能相加。[根自检与正式评分逐题对照](evidence/strict-outcome-paths.json)

## 二、怎样让错误第一次暴露

Codex 的 59 份原生根会话都记录了“先针对刚改动的代码检查，再逐步扩大测试范围”的指令。DSH 的 59 份都记录了“每次检查 Bash 退出码，失败先调查”的指令。前者促使模型从组件走到整题，后者使工具外层的“已完成”不会掩盖命令正文中的失败。下面列出的业务反例、参考算法和采样输入，均由模型在具体任务中选择；两套系统的这些提示没有预置隐藏评分答案。[逐次提示核验](evidence/error-exposure-evidence.json) · [Codex 提示源码](https://github.com/horacezoe/CodexAndDSH-/blob/01938b91a6d1ff62af46e2b5118ad78b2c0c01fe/upstream/codex-rs/protocol/src/prompts/base_instructions/default.md#L149) · [DSH Bash 提示源码](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L249)

| 方法 | 轨迹里的证据 | 能得出的结论 |
|---|---|---|
| **构造能手算答案的边界输入** | MS02 的组件和整题公开样例都过了。DSH 将“每个主题要分配一篇论文”和“论文不得复用”同时用于两个主题争一篇论文的输入。题面规定应返回 `null`，真实入口却抛出 `TypeError`，退出码 1 | 这是公开样例之外的真实实现错误。改动 `integration.py` 后，同一输入返回 `None`。DSH 最终 9/9；SP 的两项失分来自平局和并行证据用例，不能用这一个反例解释两分差距。[题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS02/instruction.md) · [DSH 原生记录，第 75–99 行](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip) |
| **组合本来单测通过的规则** | C055 中，Codex 在公开检查通过后，用模板间接引用密文，分别观察保留密文、带钥匙解封、缺钥匙三种结果。SP 的四个自测均过，检查了顶层密文遮蔽，却遗漏递归引用 | Codex 主动覆盖了两套实现行为不同的路径，其探查时输出已正确。正式 API 为 Codex 9/9、SP 8/9。这是覆盖证据，不计作一次修复。[Codex 第 9、11 步](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C055.zip) · [SP 自测代码](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C055/dynamic_v7/trace.jsonl#L1266) |
| **从函数调用走到真实交付流程** | MS30 中，Codex 单跑公开检查通过，再执行组件写产物与合并。计算输入指纹时程序首次报错：业务代码把无法 JSON 序列化的中间数值写回输入 | 切换入口暴露了副作用。修改后原链路通过，又检查了输入保持不变。该题正式评分另因完整性失败记零，此例只用来说明发现及修复过程。[Codex 第 24–28 步](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS30.zip) |
| **独立算期望，发现不一致后裁决** | MS41 中，DSH 用参考算法比较完整输出，第一次不一致后手算，发现是参考计算有误；修正参考与生成器后，固定种子比较 500 个小输入。Codex 同题另用图路径采样作近似对照 | 差异是调查线索。修正参考程序与修正生产实现应分别计数。Codex 和 DSH 均为 11/11，SP 为 5/11；观察到的检查策略不能单独解释全部分差。[DSH 原生记录](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS41.zip) · [Codex 原生记录](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS41.zip) |

## 三、拿到反例之后，怎样确认改对了

**MS11 让我们能从同一个起点比较三条执行路径。** 任务要求把组件结果按学生身份对齐后生成整题输出。局部组件检查通过，仍然可能在组合时把买家向量排错。[题面](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/tasks/MS11/instruction.md)

| 系统 | 发现错误后实际做了什么 | 正式核心 API |
|---|---|---:|
| Codex | 第 18 步整题公开检查失败，第 19 步取得实际输出；第 20–21 步局部修改生产文件 `integration.py`，按学生 ID 对齐数据；第 22 步原样重跑公开检查通过，第 23 步重建并合并组件产物 | 10/10 |
| DSH | 初版公开检查通过，后来为 14×14 输入做性能优化，引入回归。第一次修改后原检查仍失败，于是检查中间矩阵、再次修改生产代码。原公开检查、暴力参考对照、平局与性能用例均通过 | 10/10 |
| SP | 根 Agent 确实运行了整题公开检查，并打印出期望与实际的向量差异。它在状态报告中写下修复目标，此后多次得到相同诊断输出；后续轨迹未见第二次写回生产文件，最终因重复操作中止 | 1/10 |

Codex 和 SP 在看到相近的错序信号之后走向不同；DSH 则展示了第一次修复无效时怎样继续缩小范围。可以确认的有效动作有三步：**在交付工作区修改业务实现、以原来的失败输入证明错误消失、再用整题检查确认修改没有带来回归。** 这些记录不足以把九项分差全部归给排序或补丁工具。[Codex 轨迹](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS11.zip) · [DSH 轨迹，第 133–173 行](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS11.zip) · [SP 首次整题失败](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/MS11/dynamic_v7/trace.jsonl#L850)

这类行为也出现在其他题中。59 题内可从工具顺序识别出“检查失败 → 编辑 → 再检查”的有 Codex 17 题、DSH 6 题。仅靠事件顺序分不出编辑的是生产代码还是自测，也不能判断两次检查是否相同；DSH 还有一些工具回执只标记执行结束。因此这两个计数用于定位案例，不能作为两者的业务修复率。MS11 的判断额外核对了实际改动的文件、命令和原检查的退出码。[工具序列审计](evidence/strict-trace-audit.json)

源码能确认，Codex 的 `apply_patch` 和 DSH 的 `edit` 都支持定向修改并返回成败，本批分别识别到 465 次和 60 次调用。SP 有 Shell、整文件及分块写入，当前实验工具注册中缺少等价的原生局部编辑接口。DSH 还会在覆盖文件时核对调用者上次读取的版本；Codex 可以跨轮续接长命令，DSH 可以查询或取消后台作业。这些机制能帮助模型把修复写到正确版本、等到检查结束。现有轨迹对后两者的证据主要是“确实用过”，还无法估计其独立得分贡献。[Codex 工具记录](evidence/codex-followup-evidence.json) · [DSH 工具记录](evidence/dsh-followup-evidence.json) · [SP 工作区工具注册](https://github.com/xi474/SemanticParallel/blob/109a65444b3d4884fe92ec9e1c543b85df34e95d/experiments/handshake_speculation_v1_report_gate_v1/runtime/src/agent_runtime_demo/tools/workspace.py#L776)

还有一种应单独处理的中断。C069 中 SP 被卡在分工状态报告阶段，连续 123 次参数拒绝后没有回到业务实现，首轮 0/9；两套基线均为 9/9，SP 独立重放也是 9/9。这类问题需要给协议重复失败提供恢复业务操作的路径，单纯增加测试输入无法解决。[C069 原始轨迹](https://github.com/xi474/benchmark/blob/39ffdc9f498e9150b30a07401d30276d8d6c25df/semserve/20261121-v21-cms30-v1/online/on/cases/context8/C069/dynamic_v7/trace.jsonl) · [同题分数](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json)

## 四、给 SP 的改进顺序

1. **先提高发现真实缺陷的机会。** 首次形成可运行整题时，从公开题面挑一处跨组件约束，先写下可手算的输入与期望，再调用真实入口。优先挑有多个合法状态、共享约束或不同调用路径的规则。对交付型任务，再用干净目标目录重建一次。记录差异究竟来自业务代码、参考答案、无效输入还是基础设施。
2. **再提高已知缺陷的修复完成率。** 向根 Agent 保留原失败输入、期望、实际及候选版本；开放可校验的局部编辑。重复诊断且没有代码变更时，把根带回已有反例。生产代码实际改变、同一反例由失败变为通过、整题回归通过，三项分别记录。修改参考程序另归类。
3. **用配对消融区分两项收益。** 同题、同模型、同预算设置四组：原 SP、仅加强错误发现、仅加强返修、两者同时启用。真实任务比较严格通过率和新版 Reward，同时记录完整 E2E、token 和费用。在注入已知缺陷的离线样本上，计算“被真实入口触发的缺陷数／已注入缺陷数”；在确认的业务反例上，计算“生产修改后同例通过数／确认的业务反例数”，并检查新增回归。原始 59 题没有完整的缺陷真值清单，不能据此反推检出率。

本报告使用已结束的同题轨迹，结论是两类能力都值得分别验证。已有数据显示 SP 经常在有限自测通过后仍失分，也存在看到差异却未写回修复的明确个案。新方案能提高多少严格通过率，以及要为此增加多少时间和成本，须由上述配对实验回答。[源码、计时边界与原审计详表](Codex与DSH机制分析及SP严格通过率改进报告.md)
