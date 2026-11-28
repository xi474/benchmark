# Upstream59 · Nanobot、OpenCode 补跑后与官方 Supervisor 的对照

DeepSeek V4 Pro 普通模式，Upstream59 v2.1.0，59 题 × 7 个配置。Nanobot 和 OpenCode 各 7 格的工作区与评分登记表串题已修复，14 格全部取得正式评分并合回矩阵。
本轮 164 个模型请求全部结算。旧 attempt、评分与终态保存在矩阵的 `repair.details` 中。

[对照报告](报告.md) · [更新后的 59 题矩阵](seven-configuration-matrix.json) · [实验规格](实验规格与补跑边界.md) · [上版对照及 Codex／DSH 补跑](../upstream59-v4pro-supervisor-codex-dsh-rerun-20261128/README.md)

[归档清单](manifest.json) · [双端校验](input-attestations.json) · [评分与结算](completion.json)

## 14 格 trace

| Harness | 题号 | 补跑 trace | 旧 attempt | 本次终态 |
| --- | --- | --- | --- | --- |
| Nanobot | C011 | [下载 ZIP](traces/nanobot/C011.zip) | [`u59-v21-v4pro-nanobot-c011`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/C011.zip) | `normal` |
| Nanobot | C056 | [下载 ZIP](traces/nanobot/C056.zip) | [`u59-v21-v4pro-nanobot-c056`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/C056.zip) | `normal` |
| Nanobot | C062 | [下载 ZIP](traces/nanobot/C062.zip) | [`u59-v21-v4pro-nanobot-c062`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/C062.zip) | `normal` |
| Nanobot | MS12 | [下载 ZIP](traces/nanobot/MS12.zip) | [`u59-v21-v4pro-nanobot-ms12`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MS12.zip) | `normal` |
| Nanobot | MS23 | [下载 ZIP](traces/nanobot/MS23.zip) | [`u59-v21-v4pro-nanobot-ms23`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MS23.zip) | `NonZeroAgentExitCodeError` |
| Nanobot | MS30 | [下载 ZIP](traces/nanobot/MS30.zip) | [`u59-v21-v4pro-nanobot-ms30`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MS30.zip) | `NonZeroAgentExitCodeError` |
| Nanobot | MS42 | [下载 ZIP](traces/nanobot/MS42.zip) | [`u59-v21-v4pro-nanobot-ms42`](../upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot/MS42.zip) | `NonZeroAgentExitCodeError` |
| OpenCode | C011 | [下载 ZIP](traces/opencode/C011.zip) | `u59-v21-v4pro-opencode-c011` | `output_limit` |
| OpenCode | C056 | [下载 ZIP](traces/opencode/C056.zip) | `u59-v21-v4pro-opencode-c056` | `runtime_epipe_after_stop` |
| OpenCode | C062 | [下载 ZIP](traces/opencode/C062.zip) | `u59-v21-v4pro-opencode-c062` | `runtime_epipe_after_stop` |
| OpenCode | MS12 | [下载 ZIP](traces/opencode/MS12.zip) | `u59-v21-v4pro-opencode-ms12` | `output_limit` |
| OpenCode | MS23 | [下载 ZIP](traces/opencode/MS23.zip) | `u59-v21-v4pro-opencode-ms23` | `output_limit` |
| OpenCode | MS30 | [下载 ZIP](traces/opencode/MS30.zip) | `u59-v21-v4pro-opencode-ms30` | `output_limit` |
| OpenCode | MS42 | [下载 ZIP](traces/opencode/MS42.zip) | `u59-v21-v4pro-opencode-ms42` | `output_limit` |

OpenCode 的 5 格输出触顶与 2 格在模型返回 `stop` 后出现的 EPIPE 分别保留。Nanobot 有 3 格 Agent 非零退出，三格均有正式评分。

ZIP 含脱敏后的原生轨迹、资源记录、逐格网关账本和 Harbor 结果。OpenCode 原生会话、消息、工具片段和事件由 SQLite 导出为 JSONL，`case.json` 记录来源哈希和行数。OpenCode 旧 attempt 的身份、终态与评分保存在矩阵，原始轨迹仍保存在本地。
