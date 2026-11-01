# artifact_provenance_release_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 214.031 s |
| Agent exec | 176.767 s |
| Input tokens | 32088 |
| Cache hit | 16128 |
| Cache miss | 15960 |
| Output tokens | 11968 |
| Cost | $0.034585 / ¥0.2322 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 8 |
| Max concurrent tools | 3 |
| Planning level | P3 |
| Parallel width | 1 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：P3；parallel_width：1。
- 工具调用：8；最大并发：3。

Trace: `../../traces/langgraph/artifact_provenance_release_spec_v4`
