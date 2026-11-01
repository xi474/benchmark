# backup_restore_certification_spec_v4

## latte-native

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1516.985 s |
| Agent exec | 1498.513 s |
| Input tokens | 2144104 |
| Cache hit | 509056 |
| Output tokens | 148098 |
| Cost | $1.383565 / ¥9.289 |
| Tasks done | 0 / 4 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\nrun_all executed\n Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 16, in main\n    value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))\n                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/pathlib.py\", line 1027, in read |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-native/backup_restore_certification_spec_v4`
