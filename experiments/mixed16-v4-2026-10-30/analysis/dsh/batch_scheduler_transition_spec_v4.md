# batch_scheduler_transition_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 1352.192 s |
| Agent exec | 1320.99 s |
| Input tokens | 3052711 |
| Cache hit | 3036416 |
| Cache miss | 16295 |
| Output tokens | 117592 |
| Cost | $0.310388 / ¥2.0839 |
| Exception | none |
| Verifier | {"entry": "reasoning4/batch_scheduler_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| Tool calls | 43 |
| Max concurrent tools | 6 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：43；最大并发：6。

Trace: `../../traces/dsh/batch_scheduler_transition_spec_v4`
