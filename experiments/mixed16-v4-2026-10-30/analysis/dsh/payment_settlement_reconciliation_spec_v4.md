# payment_settlement_reconciliation_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 525.532 s |
| Agent exec | 495.516 s |
| Input tokens | 1089103 |
| Cache hit | 1071744 |
| Cache miss | 17359 |
| Output tokens | 47610 |
| Cost | $0.129303 / ¥0.8681 |
| Exception | none |
| Verifier | {"entry": "context8/payment_settlement_reconciliation_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count": 17} |
| Tool calls | 46 |
| Max concurrent tools | 6 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：46；最大并发：6。

Trace: `../../traces/dsh/payment_settlement_reconciliation_spec_v4`
