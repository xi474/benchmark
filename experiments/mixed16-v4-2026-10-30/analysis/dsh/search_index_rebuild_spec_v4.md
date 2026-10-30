# search_index_rebuild_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 772.384 s |
| Agent exec | 741.66 s |
| Input tokens | 1938752 |
| Cache hit | 1920384 |
| Cache miss | 18368 |
| Output tokens | 73870 |
| Cost | $0.200634 / ¥1.347 |
| Exception | none |
| Verifier | {"entry": "context8/search_index_rebuild_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 18} |
| Tool calls | 46 |
| Max concurrent tools | 8 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：46；最大并发：8。

Trace: `../../traces/dsh/search_index_rebuild_spec_v4`
