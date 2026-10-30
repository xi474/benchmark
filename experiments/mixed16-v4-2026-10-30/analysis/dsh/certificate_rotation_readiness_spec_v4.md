# certificate_rotation_readiness_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 863.961 s |
| Agent exec | 832.433 s |
| Input tokens | 1656560 |
| Cache hit | 1638656 |
| Cache miss | 17904 |
| Output tokens | 77153 |
| Cost | $0.20063 / ¥1.347 |
| Exception | none |
| Verifier | {"entry": "linux2/certificate_rotation_readiness_spec_v4", "status": "passed", "output_count": 5, "api_cases": 26, "protected_file_count": 13} |
| Tool calls | 52 |
| Max concurrent tools | 9 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：52；最大并发：9。

Trace: `../../traces/dsh/certificate_rotation_readiness_spec_v4`
