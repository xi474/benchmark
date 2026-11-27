# Upstream59 · 补跑后与官方 LangGraph Supervisor 的对照

DeepSeek V4 Pro 普通模式 · 59 题 × 7 个配置。Codex 6 格、DSH 7 格的工作区与评分身份修复补跑均已验收。
原评测的 13 条 attempt 仍可按下表查看。5 条触及累计 token 上限的新记录同时保留正式评分和终态。

[更新后的报告](报告.md) · [59 题矩阵](seven-configuration-matrix.json) · [实验规格](实验规格与补跑边界.md) · [补跑前报告与图表](history/补跑前对照.md) · [Supervisor 原 59 题配对](history/Supervisor原59题配对.md)

[归档校验清单](manifest.json) · [双端输入校验](input-attestations.json) · [账本与结果](completion.json)

## 13 格补跑 trace

| Harness | 题号 | 本次 trace | 原 attempt trace |
| --- | --- | --- | --- |
| codex | C056 | [补跑](traces/codex/C056.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C056.zip) |
| codex | C062 | [补跑](traces/codex/C062.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/C062.zip) |
| codex | MS12 | [补跑](traces/codex/MS12.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS12.zip) |
| codex | MS23 | [补跑](traces/codex/MS23.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS23.zip) |
| codex | MS30 | [补跑](traces/codex/MS30.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS30.zip) |
| codex | MS42 | [补跑](traces/codex/MS42.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/codex/MS42.zip) |
| dsh | C011 | [补跑](traces/dsh/C011.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C011.zip) |
| dsh | C056 | [补跑](traces/dsh/C056.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C056.zip) |
| dsh | C062 | [补跑](traces/dsh/C062.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C062.zip) |
| dsh | MS12 | [补跑](traces/dsh/MS12.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS12.zip) |
| dsh | MS23 | [补跑](traces/dsh/MS23.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS23.zip) |
| dsh | MS30 | [补跑](traces/dsh/MS30.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS30.zip) |
| dsh | MS42 | [补跑](traces/dsh/MS42.zip) | [原件发布副本](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS42.zip) |

ZIP 含原生会话、工具与资源遥测、运行终态和本格的网关记录。发布版已脱敏。
每格在 `case.json` 中提供原始与发布文件摘要、评分和原 attempt 身份。
