# certificate_rotation_readiness_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 201.153 s |
| Agent exec | 167.856 s |
| Input tokens | 66875 |
| Cache hit | 53888 |
| Cache miss | 12987 |
| Output tokens | 11330 |
| Cost | $0.03219 / ¥0.2161 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 20 |
| Max concurrent tools | 1 |
| Planning level | None |
| Parallel width | None |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：None；parallel_width：None。
- 工具调用：20；最大并发：1。

Trace: `../../traces/langgraph/certificate_rotation_readiness_spec_v4`
