# observability_retention_upgrade_spec_v4

## latte-native

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1506.334 s |
| Agent exec | 1488.937 s |
| Input tokens | 1486237 |
| Cache hit | 391552 |
| Output tokens | 153147 |
| Cost | $1.034337 / ¥6.9443 |
| Tasks done | 3 / 4 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-native/observability_retention_upgrade_spec_v4`
