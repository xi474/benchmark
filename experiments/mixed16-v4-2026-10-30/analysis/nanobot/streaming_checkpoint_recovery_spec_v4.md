# streaming_checkpoint_recovery_spec_v4

## nanobot

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 459.429 s |
| Agent exec | 427.948 s |
| Input tokens | 202957 |
| Cache hit | 193536 |
| Cache miss | 9421 |
| Output tokens | 33824 |
| Cost | $0.077447 / ¥0.52 |
| Exception | NonZeroAgentExitCodeError |
| Verifier | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 10, in main\n    assert (ROOT/name).is_file(), 'missing implementation: '+name\n           ^^^^^^^^^^^^^^^^^^^^^\nAssertionError: missing implementation: run_all.py\n"} |
| Tool calls | 23 |
| Max concurrent tools | 2 |
| Branch opened | 6 |

Trace: `traces/nanobot/streaming_checkpoint_recovery_spec_v4`
