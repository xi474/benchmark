# SP 严格通过率改进报告 · 2026 年 11 月 25 日

| 阅读目的 | 报告 |
|---|---|
| 确定 SP 的改造顺序，查看模块改动、断网验收与消融方案 | [SP 严格通过率改进实施手册](SP严格通过率改进实施手册-20261125.md) |
| 了解 Nanobot 怎样发现交付缺陷、精确修改生产文件，以及 SP 可以怎样借鉴 | [Nanobot 工具链分析与 SP 改进建议](Nanobot工具链分析与SP改进建议.md) |
| 横向核查 SP、Codex、DSH、Nanobot 各自有哪些工具和实际调用证据 | [四套 Harness 工具链对照](四套Harness工具链对照与SP改进方案.md) |

同题配对中，SP 和 Nanobot 均严格通过 19 题，仅 SP 通过 10 题，仅 Nanobot 通过 13 题，双方均未过 17 题。SP 使用公开失败后按规则重放的选定结果，Nanobot 使用正式矩阵的历史选定试次。建议的工程改动仍待同条件消融验证。[59 题配对](evidence/nanobot-vs-sp-retest-20261125.json) · [SP 全量复测原报告](../../upstream59-full-retest-v31-20261125/analysis/全量59题benchmark复测报告-20261125.md) · [SP 运行时补丁说明](../../upstream59-full-retest-v31-20261125/runtime-patches/README.md)

### 复核单文件编辑证据

在包含原生轨迹归档的完整仓库中，从仓库根目录执行以下命令。脚本使用 Python 标准库，读取 59 份 Nanobot 原生轨迹，核对每次编辑之前模型是否已经成功写过同一路径，以及待替换片段在最近一次整写中出现几次。

```sh
python results/upstream59-sp-failure-analysis-20261124/updates-20261125/evidence/nanobot-edit-anchors-audit.py
```

125 次精确编辑中，123 次此前已在同一 Agent 下成功整写过该文件，112 次的旧片段在最近整写中逐字出现且唯一。这项统计描述工具使用行为。[逐次核验数据](evidence/nanobot-edit-anchors-59.json) · [原生轨迹目录](../../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/) · [11 月 24 日报告与汇报材料](../README.md)
