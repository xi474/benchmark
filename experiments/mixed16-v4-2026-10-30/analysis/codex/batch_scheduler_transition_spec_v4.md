# batch_scheduler_transition_spec_v4

## codex

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 2345.86 s |
| Agent exec | 2316.964 s |
| Input tokens | 6958844 |
| Cache hit | 6843136 |
| Cache miss | 115708 |
| Output tokens | 150912 |
| Cost | $0.525722 / ¥3.5296 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: engines/worker_assignment case 3"} |
| Tool calls | 80 |
| Max concurrent tools | 1 |
| Branch opened | not applicable |

## 执行分析

- 结论：未通过外部 verifier：held-out API mismatch: engines/worker_assignment case 3
- 工具调用：80 次；最大并发工具：1。
- E2E 为 2345.86 s，其中 agent execution 为 2316.964 s。
- 成本：$0.525722 / ¥3.5296。

Trace: `../../traces/codex/batch_scheduler_transition_spec_v4`
