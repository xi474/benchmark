# backup_restore_certification_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 734.115 s |
| Agent exec | 702.545 s |
| Input tokens | 1800082 |
| Cache hit | 1782144 |
| Cache miss | 17938 |
| Output tokens | 66428 |
| Cost | $0.182574 / ¥1.2258 |
| Exception | none |
| Verifier | {"entry": "linux2/backup_restore_certification_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 13} |
| Tool calls | 50 |
| Max concurrent tools | 9 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：50；最大并发：9。

Trace: `../../traces/dsh/backup_restore_certification_spec_v4`
