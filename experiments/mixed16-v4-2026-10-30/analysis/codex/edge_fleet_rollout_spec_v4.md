# edge_fleet_rollout_spec_v4

## codex

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1649.617 s |
| Agent exec | 1619.297 s |
| Input tokens | 4358773 |
| Cache hit | 4336768 |
| Cache miss | 22005 |
| Output tokens | 91562 |
| Cost | $0.291225 / ¥1.9552 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: engines/rollout_order case 3"} |
| Tool calls | 55 |
| Max concurrent tools | 3 |
| Branch opened | not applicable |

## 执行分析

- 结论：未通过外部 verifier：held-out API mismatch: engines/rollout_order case 3
- 工具调用：55 次；最大并发工具：3。
- E2E 为 1649.617 s，其中 agent execution 为 1619.297 s。
- 成本：$0.291225 / ¥1.9552。

Trace: `../../traces/codex/edge_fleet_rollout_spec_v4`
