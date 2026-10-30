# warehouse_cutover_assurance_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 585.244 s |
| Agent exec | 554.3 s |
| Input tokens | 1233103 |
| Cache hit | 1200896 |
| Cache miss | 32207 |
| Output tokens | 55381 |
| Cost | $0.157331 / ¥1.0563 |
| Exception | none |
| Verifier | {"entry": "multistage4/warehouse_cutover_assurance_spec_v4", "status": "passed", "output_count": 8, "api_cases": 37, "protected_file_count": 18} |
| Tool calls | 41 |
| Max concurrent tools | 1 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：41；最大并发：1。

Trace: `../../traces/dsh/warehouse_cutover_assurance_spec_v4`
