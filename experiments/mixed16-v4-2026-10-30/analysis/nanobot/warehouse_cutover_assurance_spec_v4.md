# warehouse_cutover_assurance_spec_v4

## nanobot

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 645.691 s |
| Agent exec | 615.272 s |
| Input tokens | 2917940 |
| Cache hit | 2878080 |
| Cache miss | 39860 |
| Output tokens | 53371 |
| Cost | $0.1953 / ¥1.3112 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: views/repair_waves case 1"} |
| Tool calls | 69 |
| Max concurrent tools | 1 |
| Branch opened | 12 |

## 执行分析

- 结论：未通过外部 verifier：held-out API mismatch: views/repair_waves case 1
- 工具调用：69 次；最大并发工具：1。
- E2E 为 645.691 s，其中 agent execution 为 615.272 s。
- 成本：$0.1953 / ¥1.3112。

Trace: `../../traces/nanobot/warehouse_cutover_assurance_spec_v4`
