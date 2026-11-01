# search_index_rebuild_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 184.199 s |
| Agent exec | 157.467 s |
| Input tokens | 24320 |
| Cache hit | 14208 |
| Cache miss | 10112 |
| Output tokens | 11315 |
| Cost | $0.02939 / ¥0.1973 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 23 |
| Max concurrent tools | 1 |
| Planning level | P3 |
| Parallel width | 1 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：P3；parallel_width：1。
- 工具调用：23；最大并发：1。

Trace: `../../traces/langgraph/search_index_rebuild_spec_v4`
