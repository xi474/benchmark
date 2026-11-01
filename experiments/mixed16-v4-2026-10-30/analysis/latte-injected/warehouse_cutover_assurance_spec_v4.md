# warehouse_cutover_assurance_spec_v4

## latte-injected

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1451.209 s |
| Agent exec | 1435.229 s |
| Input tokens | 2252279 |
| Cache hit | 465536 |
| Output tokens | 109566 |
| Cost | $1.406433 / ¥9.4425 |
| Tasks done | 0 / 7 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-injected/warehouse_cutover_assurance_spec_v4`
