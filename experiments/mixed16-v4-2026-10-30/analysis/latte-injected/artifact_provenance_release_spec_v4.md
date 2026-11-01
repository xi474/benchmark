# artifact_provenance_release_spec_v4

## latte-injected

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1252.905 s |
| Agent exec | 1236.272 s |
| Input tokens | 1709119 |
| Cache hit | 455424 |
| Output tokens | 94349 |
| Cost | $1.024269 / ¥6.8767 |
| Tasks done | 1 / 7 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-injected/artifact_provenance_release_spec_v4`
