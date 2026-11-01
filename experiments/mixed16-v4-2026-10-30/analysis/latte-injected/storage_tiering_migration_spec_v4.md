# storage_tiering_migration_spec_v4

## latte-injected

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1367.697 s |
| Agent exec | 1350.416 s |
| Input tokens | 2212404 |
| Cache hit | 434944 |
| Output tokens | 120497 |
| Cost | $1.421276 / ¥9.5422 |
| Tasks done | 0 / 7 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-injected/storage_tiering_migration_spec_v4`
