# api_deprecation_campaign_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 1.0 |
| E2E | 952.411 s |
| Agent exec | 920.755 s |
| Input tokens | 3165071 |
| Cache hit | 3140224 |
| Cache miss | 24847 |
| Output tokens | 81229 |
| Cost | $0.246317 / ¥1.6537 |
| Exception | none |
| Verifier | {"entry": "reasoning4/api_deprecation_campaign_spec_v4", "status": "passed", "output_count": 5, "api_cases": 28, "protected_file_count": 12} |
| Tool calls | 54 |
| Max concurrent tools | 3 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：通过外部 verifier。
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：54；最大并发：3。

Trace: `../../traces/dsh/api_deprecation_campaign_spec_v4`
