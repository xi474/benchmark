# regional_failover_readiness_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 598.359 s |
| Agent exec | 566.777 s |
| Input tokens | 1787176 |
| Cache hit | 1756928 |
| Cache miss | 30248 |
| Output tokens | 59432 |
| Cost | $0.176291 / ¥1.1836 |
| Exception | none |
| Verifier | {"entry": "multistage4/regional_failover_readiness_spec_v4", "status": "passed", "output_count": 9, "api_cases": 37, "protected_file_count": 18} |
| Tool calls | 63 |
| Max concurrent tools | 8 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：63；最大并发：8。

Trace: `../../traces/dsh/regional_failover_readiness_spec_v4`
