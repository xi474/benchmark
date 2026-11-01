# payment_settlement_reconciliation_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 188.613 s |
| Agent exec | 153.749 s |
| Input tokens | 35886 |
| Cache hit | 26368 |
| Cache miss | 9518 |
| Output tokens | 11316 |
| Cost | $0.029268 / ¥0.1965 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 19 |
| Max concurrent tools | 1 |
| Planning level | None |
| Parallel width | None |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"}
- LangGraph planning：None；parallel_width：None。
- 工具调用：19；最大并发：1。

Trace: `../../traces/langgraph/payment_settlement_reconciliation_spec_v4`
