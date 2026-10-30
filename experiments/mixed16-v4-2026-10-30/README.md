# mixed16-v4 Codex / OpenCode / Nanobot / DSH 执行 trace 与逐题分析

数据日期：2026-10-30  
模型：`deepseek-v4-pro`  
任务集：`mixed16-precise-spec-v4`  
Harness：Codex / OpenCode / Nanobot / DSH  
Trial：64（16 × 4）

## 内容

```text
traces/
  codex/<task>/codex.txt
  opencode/<task>/opencode.txt
  nanobot/<task>/nanobot.txt
  nanobot/<task>/events-v2.jsonl
  nanobot/<task>/summary.json
  dsh/<task>/dsh-runner.log
  dsh/<task>/dsh-stream.jsonl
  dsh/<task>/summary.json
  dsh/<task>/events-v2.jsonl

analysis/
  codex/<task>.md
  opencode/<task>.md
  nanobot/<task>.md
  dsh/<task>.md
  summary.csv
  README.md

results/
  <harness>/<task>/summary.json
```

## 汇总

```text
完成：64 / 64
Reward 1：39
ACC：60.94%
E2E 平均：1096.8s = 18.28 min
总成本：$11.0719 / ¥74.3350
```

| Harness | Reward 1 | ACC | E2E 平均 | 成本（USD） | 成本（CNY） |
|---|---:|---:|---:|---:|---:|
| DSH | 13/16 | 81.25% | 14.34 min | $3.4059 | ¥22.8665 |
| Codex | 10/16 | 62.50% | 25.19 min | $3.6351 | ¥24.4053 |
| OpenCode | 10/16 | 62.50% | 17.53 min | $0.4662 | ¥3.1300 |
| Nanobot | 6/16 | 37.50% | 16.06 min | $3.5647 | ¥23.9327 |

## 说明

- 原始 `opencode.db` **未上传**，因为其中可能包含本地 credential/account 数据。
- OpenCode 的工具并发统计由本地 SQLite `part.data.state.time.start/end` 计算，不随 DB 一起发布。
- Codex 有 3 个 success trial 因 `max_output_tokens` 截断，没有 `turn.completed.usage`，成本记为 missing，未填 0。
- DSH 本轮使用 `HARNESS_DSH_CONDITION=delegation_enabled` 和 delegation policy，但 telemetry 中 `subagent_count` 仍为 0；其 ACC 提升不能直接归因于实际 subagent 并行。
- 所有 trace 已对 API key 做脱敏。
- 任务集与 verifier 说明见仓库根目录的 `mixed16-precise-spec-v4/`。

## 数据口径

- E2E：`result.started_at → finished_at`
- Agent exec：`agent_execution.started_at → finished_at`
- 成本：`deepseek-v4-pro` off-peak
  - cache hit：$0.022 / 1M
  - cache miss：$0.66 / 1M
  - output：$1.98 / 1M
- 汇率：1 USD = 6.7138 CNY
