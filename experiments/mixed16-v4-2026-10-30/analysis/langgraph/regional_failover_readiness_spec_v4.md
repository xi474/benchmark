# regional_failover_readiness_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 197.718 s |
| Agent exec | 167.353 s |
| Input tokens | 42028 |
| Cache hit | 27008 |
| Cache miss | 15020 |
| Output tokens | 11511 |
| Cost | $0.033299 / ¥0.2236 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 24 |
| Max concurrent tools | 1 |
| Planning level | P3 |
| Parallel width | 1 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：P3；parallel_width：1。
- 工具调用：24；最大并发：1。

Trace: `../../traces/langgraph/regional_failover_readiness_spec_v4`
