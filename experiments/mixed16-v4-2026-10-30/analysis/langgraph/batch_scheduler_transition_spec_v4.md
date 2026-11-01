# batch_scheduler_transition_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 422.975 s |
| Agent exec | 386.251 s |
| Input tokens | 362510 |
| Cache hit | 329984 |
| Cache miss | 32526 |
| Output tokens | 51599 |
| Cost | $0.130893 / ¥0.8788 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 83 |
| Max concurrent tools | 1 |
| Planning level | P3 |
| Parallel width | 3 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：P3；parallel_width：3。
- 工具调用：83；最大并发：1。

Trace: `../../traces/langgraph/batch_scheduler_transition_spec_v4`
