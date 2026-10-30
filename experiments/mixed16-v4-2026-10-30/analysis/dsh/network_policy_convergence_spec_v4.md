# network_policy_convergence_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 779.506 s |
| Agent exec | 750.714 s |
| Input tokens | 1985088 |
| Cache hit | 1967104 |
| Cache miss | 17984 |
| Output tokens | 77140 |
| Cost | $0.207883 / ¥1.3957 |
| Exception | none |
| Verifier | {"entry": "linux2/network_policy_convergence_spec_v4", "status": "passed", "output_count": 5, "api_cases": 31, "protected_file_count": 13} |
| Tool calls | 57 |
| Max concurrent tools | 9 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：57；最大并发：9。

Trace: `../../traces/dsh/network_policy_convergence_spec_v4`
