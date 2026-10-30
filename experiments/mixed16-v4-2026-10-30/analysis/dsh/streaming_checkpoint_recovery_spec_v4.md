# streaming_checkpoint_recovery_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 675.863 s |
| Agent exec | 645.456 s |
| Input tokens | 1109058 |
| Cache hit | 1090944 |
| Cache miss | 18114 |
| Output tokens | 64283 |
| Cost | $0.163236 / ¥1.0959 |
| Exception | none |
| Verifier | {"entry": "context8/streaming_checkpoint_recovery_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count": 17} |
| Tool calls | 46 |
| Max concurrent tools | 8 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：46；最大并发：8。

Trace: `../../traces/dsh/streaming_checkpoint_recovery_spec_v4`
