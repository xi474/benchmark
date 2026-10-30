# api_deprecation_campaign_spec_v4

## nanobot

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 582.413 s |
| Agent exec | 553.741 s |
| Input tokens | 199892 |
| Cache hit | 191360 |
| Cache miss | 8532 |
| Output tokens | 33996 |
| Cost | $0.077153 / ¥0.518 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 16 |
| Max concurrent tools | 1 |
| Branch opened | 5 |

## 执行分析

- 结论：未通过外部 verifier：local execution failed:  Traceback (most recent call last):
  File "/app/check.py", line 23, in <module>
    if __name__=='__main__': main()
                             ^^^^^^
  File "/app/check.py", line 10, in main
    assert (ROOT/name).is_file(), 'missing implementation: '+name
           ^^^^^^^^^^^^^^^^^^^^^
AssertionError: missing implementation: run_all.py
 终止异常：`NonZeroAgentExitCodeError`。
- 工具调用：16 次；最大并发工具：1。
- E2E 为 582.413 s，其中 agent execution 为 553.741 s。
- 成本：$0.077153 / ¥0.518。

Trace: `../../traces/nanobot/api_deprecation_campaign_spec_v4`
