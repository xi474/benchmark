# observability_retention_upgrade_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 201.271 s |
| Agent exec | 163.284 s |
| Input tokens | 41663 |
| Cache hit | 31360 |
| Cache miss | 10303 |
| Output tokens | 11115 |
| Cost | $0.029498 / ¥0.1980 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 14 |
| Max concurrent tools | 1 |
| Planning level | None |
| Parallel width | None |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：None；parallel_width：None。
- 工具调用：14；最大并发：1。

Trace: `../../traces/langgraph/observability_retention_upgrade_spec_v4`
