# tenant_quota_rebalance_spec_v4

## latte-native

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 1242.709 s |
| Agent exec | 1225.084 s |
| Input tokens | 651546 |
| Cache hit | 305280 |
| Output tokens | 95473 |
| Cost | $0.424288 / ¥2.8486 |
| Tasks done | 1 / 2 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 16, in main\n    value=json.loads((ROOT/c['output']).read_text(encoding='utf-8'))\n                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n  File \"/usr/local/lib/python3.12/pathlib.py\", line 1027, in read_text\n    with self.open(mode='r', |

## 模式说明

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 预编译组件任务，属于注入提示/固定任务版本。

Trace: `../../traces/latte-native/tenant_quota_rebalance_spec_v4`
