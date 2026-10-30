# artifact_provenance_release_spec_v4

## dsh

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 813.15 s |
| Agent exec | 779.142 s |
| Input tokens | 1961474 |
| Cache hit | 1910272 |
| Cache miss | 51202 |
| Output tokens | 78681 |
| Cost | $0.231608 / ¥1.555 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: views/release_risk case 1"} |
| Tool calls | 43 |
| Max concurrent tools | 1 |
| Subagent count | 0 |
| Planning level | P0 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "held-out API mismatch: views/release_risk case 1"}
- DSH condition：`delegation_enabled`。
- telemetry 中 `subagent_count = 0`，`planning_level = P0`。
- 工具调用：43；最大并发：1。

Trace: `../../traces/dsh/artifact_provenance_release_spec_v4`
