# warehouse_cutover_assurance_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 190.077 s |
| Agent exec | 162.58 s |
| Input tokens | 66239 |
| Cache hit | 48512 |
| Cache miss | 17727 |
| Output tokens | 12789 |
| Cost | $0.038089 / ¥0.2557 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 21 |
| Max concurrent tools | 1 |
| Planning level | P3 |
| Parallel width | 1 |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：P3；parallel_width：1。
- 工具调用：21；最大并发：1。

Trace: `../../traces/langgraph/warehouse_cutover_assurance_spec_v4`
