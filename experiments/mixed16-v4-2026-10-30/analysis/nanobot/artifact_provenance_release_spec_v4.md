# artifact_provenance_release_spec_v4

## nanobot

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 551.265 s |
| Agent exec | 523.693 s |
| Input tokens | 241150 |
| Cache hit | 214144 |
| Cache miss | 27006 |
| Output tokens | 33752 |
| Cost | $0.089364 / ¥0.6 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 20 |
| Max concurrent tools | 1 |
| Branch opened | 4 |

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
- 工具调用：20 次；最大并发工具：1。
- E2E 为 551.265 s，其中 agent execution 为 523.693 s。
- 成本：$0.089364 / ¥0.6。

Trace: `../../traces/nanobot/artifact_provenance_release_spec_v4`
