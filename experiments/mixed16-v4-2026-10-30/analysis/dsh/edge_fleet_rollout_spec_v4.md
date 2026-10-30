# edge_fleet_rollout_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 1209.899 s |
| Agent exec | 1177.151 s |
| Input tokens | 3642526 |
| Cache hit | 3618944 |
| Cache miss | 23582 |
| Output tokens | 100975 |
| Cost | $0.295111 / ¥1.9813 |
| Exception | none |
| Verifier | {"entry": "reasoning4/edge_fleet_rollout_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| Tool calls | 48 |
| Max concurrent tools | 3 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：48；最大并发：3。

Trace: `../../traces/dsh/edge_fleet_rollout_spec_v4`
