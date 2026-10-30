# search_index_rebuild_spec_v4

## nanobot

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 967.998 s |
| Agent exec | 938.242 s |
| Input tokens | 4609455 |
| Cache hit | 4577536 |
| Cache miss | 31919 |
| Output tokens | 77929 |
| Cost | $0.276072 / ¥1.8535 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: cutover_plan case 6"} |
| Tool calls | 92 |
| Max concurrent tools | 1 |
| Branch opened | 13 |

## 执行分析

- 结论：未通过外部 verifier：held-out API mismatch: cutover_plan case 6
- 工具调用：92 次；最大并发工具：1。
- E2E 为 967.998 s，其中 agent execution 为 938.242 s。
- 成本：$0.276072 / ¥1.8535。

Trace: `../../traces/nanobot/search_index_rebuild_spec_v4`
