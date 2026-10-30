# artifact_provenance_release_spec_v4

## opencode

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 563.264 s |
| Agent exec | 535.914 s |
| Input tokens | 78934 |
| Cache hit | 78934 |
| Cache miss | 0 |
| Output tokens | 8430 |
| Cost | $0.018428 / ¥0.1237 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "incorrect output: outputs/audit_assignment.json"} |
| Tool calls | 35 |
| Max concurrent tools | 1 |
| Branch opened | not applicable |

## 执行分析

- 结论：未通过外部 verifier：incorrect output: outputs/audit_assignment.json
- 工具调用：35 次；最大并发工具：1。
- E2E 为 563.264 s，其中 agent execution 为 535.914 s。
- 成本：$0.018428 / ¥0.1237。

Trace: `../../traces/opencode/artifact_provenance_release_spec_v4`
