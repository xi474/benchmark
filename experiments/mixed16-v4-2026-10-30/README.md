# mixed16-v4 执行 trace 与逐题分析

数据日期：2026-10-30 / 2026-11-01  
模型：`deepseek-v4-pro`  
任务集：`mixed16-precise-spec-v4`  
Trial：112（16 × 7 个实验条件）

## 实验条件

```text
Codex
OpenCode
Nanobot
DSH
LangGraph
LATTE 原生
LATTE 注入提示
```

## LATTE 两种版本

- **LATTE 原生**：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务，不注入预编译组件任务。
- **LATTE 注入提示**：adapter 读取 `/opt/latte-task` 的预编译组件任务，属于注入提示/固定任务版本。

两个版本分别位于：

```text
traces/latte-native/、analysis/latte-native/、results/latte-native/
traces/latte-injected/、analysis/latte-injected/、results/latte-injected/
```

## 内容

```text
traces/
  codex/<task>/codex.txt
  opencode/<task>/opencode.txt
  nanobot/<task>/...
  dsh/<task>/...
  langgraph/<task>/...
  latte-native/<task>/...
  latte-injected/<task>/...

analysis/
  <harness>/<task>.md
  summary.csv
  README.md

results/
  <harness>/<task>/summary.json
```

## 汇总

```text
完成：112 / 112
Reward 1：40
ACC：35.71%
E2E 平均：921.8s = 15.36 min
总成本：$30.6583 / ¥205.8336
missing cost：31
```

| Harness | Reward 1 | ACC | E2E 平均 | 成本（USD） | 成本（CNY） |
|---|---:|---:|---:|---:|---:|
| DSH | 13/16 | 81.25% | 14.34 min | $3.4059 | ¥22.8667 |
| Codex | 10/16 | 62.50% | 25.19 min | $3.6351 | ¥24.4053 |
| OpenCode | 10/16 | 62.50% | 17.53 min | $0.4662 | ¥3.1301 |
| Nanobot | 6/16 | 37.50% | 16.06 min | $3.5647 | ¥23.9329 |
| LangGraph | 1/16 | 6.25% | 5.40 min | $1.2401 | ¥8.3254 |
| LATTE 原生 | 0/16 | 0.00% | 6.57 min | $3.7580 | ¥25.2302 |
| LATTE 注入提示 | 0/16 | 0.00% | 22.46 min | $14.5883 | ¥97.9430 |

## 说明

- 原始 `opencode.db` **未上传**，因为其中可能包含本地 credential/account 数据。
- Codex 有 3 个 success trial 因 `max_output_tokens` 截断，没有 `turn.completed.usage`，成本记为 missing。
- DSH 本轮使用 `delegation_enabled`，但 telemetry `subagent_count` 为 0；不能归因于实际 subagent 并行。
- LATTE 原生有 12 个 trial 没有可读的 `latte_result`，token/cost 记为 missing。
- LATTE 两个版本在本批 16 题上均未通过外部 verifier，Reward 1 为 0。
- 所有 trace 已对 API key 做脱敏。

## 数据口径

- E2E：`result.started_at → finished_at`
- Agent exec：`agent_execution.started_at → finished_at`
- 成本：`deepseek-v4-pro` off-peak
  - cache hit：$0.022 / 1M
  - cache miss：$0.66 / 1M
  - output：$1.98 / 1M
- 汇率：1 USD = 6.7138 CNY

## 反例验证行为分析与源码证据

[Codex / OpenCode：找反例、修复与再验证](counterexample-review-2026-10-31/README.md)。包含可直接浏览的源码快照、32 份原生 trace、3 个详细案例结果，以及从运行事件提取的测试脚本。
