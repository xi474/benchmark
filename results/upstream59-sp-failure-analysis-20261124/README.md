# SP、Codex 与 DSH 的严格通过率分析

Upstream59 · DeepSeek V4 Pro 普通模式 · 2026 年 11 月 24 日

这份评审包回答三个问题：SP 在哪些题的哪些业务检查失分；Codex 和 DSH 在公开检查通过后怎样发现并修复错误；哪些机制值得移植或改造，以及怎样用同题实验验收。原始数据来自本仓库 release 分支已发布的 59 题矩阵。SP 的首轮与按公开失败规则采用重放的结果分别统计。

## 阅读与下载

| 想看什么 | 材料 |
|---|---|
| 给同事组会汇报 | [下载 16 页 PPT，含逐页讲者备注](slides/sp-codex-dsh-strict-pass.pptx?raw=true) · [PPT 页码与实施方案对照](SP工具与验证机制适配报告.md#ppt-map) |
| 每道失分题错在哪里、可以怎样修 | [SP 的 59 题逐题失分与改进报告](SP的59题逐题失分与改进报告.md)，含 59 题索引、31 道当前未严格通过题、3 道重放恢复题、134 个当前失败 API 的编号与证据 |
| SP 的工程改造和验收 | [严格通过率改进与工程实施方案](SP工具与验证机制适配报告.md)，含局部编辑、独立验证、分支合并与规则归属、真实业务入口、异常恢复和最终版本复验 |
| Codex、DSH 会不会构造反例；一次解题何时结束 | [机制、原生例证与消融方案](SP工具与验证机制适配报告.md#counterexamples) · [DSH 59 题自造场景索引](DSH自造场景逐题索引.md) · [DSH 公开检查后的逐题自测审计](DSH公开检查后的59题自测审计.md) |
| 导出、筛选或重算 | [59 题逐题 CSV](data/tasks.csv) · [含各题首轮、重放、采纳身份和失败项的 JSON](data/review.json) · [复核与导出说明](tools/README.md) · [Python 脚本](tools/verify_review.py) · [包内文件 SHA-256](SHA256SUMS) |
| 图表与原始依据 | [七系统首轮图（SVG）](../upstream59-v21-semserve-vs-six-harnesses-20261123/figure-1-first-run.svg) · [重放图（SVG）](../upstream59-v21-semserve-vs-six-harnesses-20261123/figure-2-replay.svg) · [对照报告及 PNG、逐题指标](../upstream59-v21-semserve-vs-six-harnesses-20261123/README.md) · [177 份原生 trace 归档与清单](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/README.md) |

## 已核验的结果

| SP 口径 | 公开通过 | 严格通过 | 核心业务 API | Reward／138 |
|---|---:|---:|---:|---:|
| 首轮 | 50/59 | 25/59 | 633/803 | 78.469237 |
| 含公开失败后独立重放 | 56/59 | 28/59 | 669/803 | 85.361619 |

9 次独立重放都计入代价，其中 6 次采用了新提交。59 个首轮和 9 个重放共有 68 份正式评分回执。新设计提高严格通过率的幅度仍待配对实验；报告内的条件增量标为情景测算。[逐题回执与重放选择规则](SP的59题逐题失分与改进报告.md#replays) · [工作区 reward 政策](../../scoring/reward-policy-v1.0.json)

DSH 的 53 题能在解题时定位到公开检查通过，其中 45 题又执行了新业务输入。按场景去重，共 299 个，平均 5.64 个/可定位题。MS02、MP15 有证据确认新输入揭示了生产实现错误，修改后原例通过。Codex 在 C007、C058 也有这样的例证，其全库触发率未按该口径普查。通过率和因果效果要分别解释。[逐题行为与计数边界](DSH自造场景逐题索引.md)

## 证据与复核

[逐题证据目录](evidence/)收录逐题诊断、离线探针首差、可选检查、DSH 场景标注及自测审计。[机制分析与历史参考](references/)收录实施方案引用的报告及配套证据。正式回执和原生 trace 沿用本仓已有的冻结数据。历史派生表里的 `capstone-runs/` 与 `experiment-outputs/` 是去除个人目录后的试次来源标识，可下载的原生证据另有仓库链接。离线探针复现的是归档候选，开发建议使用的自造输入不参与正式计分。发给解题 Agent 的输入仍以基准正式的公开材料为准。

在完整的 `release` 检出目录中运行以下命令，脚本使用 Python 标准库，读取现成的评分与归档，验证后输出首轮、重放和场景统计。加 `--output-dir` 可把逐题数据重新导出到新目录。

```sh
python results/upstream59-sp-failure-analysis-20261124/tools/verify_review.py
```

当前包的统计对应 [2026-11-24 发布前的冻结提交](https://github.com/xi474/benchmark/tree/00d32858637689c0668c71303d4d5b79d00b1093)。PPT 的 SHA-256 为 `287e192e9f0b92cabebe5517046db77b55670332e0c943b5648604d55479bdf6`。公开材料中的本机路径改为仓库定位，正式失败原因、异常类型和未知状态保留。
