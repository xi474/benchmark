# api_deprecation_campaign_spec_v4

## opencode

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 801.454 s |
| Agent exec | 772.009 s |
| Input tokens | 103196 |
| Cache hit | 103196 |
| Cache miss | 0 |
| Output tokens | 11218 |
| Cost | $0.024482 / ¥0.1644 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "held-out API mismatch: engines/notice_windows case 5"} |
| Tool calls | 38 |
| Max concurrent tools | 2 |
| Branch opened | not applicable |

## 执行分析

- 结论：未通过外部 verifier：held-out API mismatch: engines/notice_windows case 5
- 工具调用：38 次；最大并发工具：2。
- E2E 为 801.454 s，其中 agent execution 为 772.009 s。
- 成本：$0.024482 / ¥0.1644。

Trace: `../../traces/opencode/api_deprecation_campaign_spec_v4`
