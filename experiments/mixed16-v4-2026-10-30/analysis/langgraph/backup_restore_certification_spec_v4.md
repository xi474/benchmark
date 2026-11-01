# backup_restore_certification_spec_v4

## langgraph

| 指标 | 值 |
|---|---|
| Reward | 0.0 |
| E2E | 638.984 s |
| Agent exec | 603.519 s |
| Input tokens | 836366 |
| Cache hit | 785280 |
| Cache miss | 51086 |
| Output tokens | 74854 |
| Cost | $0.199204 / ¥1.3374 |
| Exception | none |
| Verifier | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/products/backup_graph/render.py\", line 4, in <module>\n    from model import load_payload\n  File \"/app/products/backup_graph/model.py\", line 1, in <module>\n    raise NotImplementedError('implement model.py')\nNotImplementedError: implement model.py\nTraceback (most recent call last):\n  File \"/app/run_all.py\", line 122, in <module>\n    main()\n  File \"/app/run_all. |
| Tool calls | 98 |
| Max concurrent tools | 2 |
| Planning level | None |
| Parallel width | None |

## 执行分析

- 结论：未通过外部 verifier：{"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/products/backup_graph/render.py\", line 4, in <module>\n    from model import load_payload\n  File \"/app/products/backup_graph/model.py\", line 1, in <module>\n    raise NotImplementedError('implement model.py')\nNotImplementedError: implement model.py\nTraceback (most recent call last):\n  File \"/app/run_all.py\", line 122, in <module>\n    main()\n  File \"/app/run_all.py\", line 103, in main\n    subprocess.run(\n  File \"/usr/local/lib/python3.12/subprocess.py\", line 571, in run\n    raise CalledProcessError(retcode, process.args,\nsubprocess.CalledProcessError: Command '['/installed-agent/langgraph-venv/bin/python3', '/app/products/backup_graph/render.py']' returned non-zero exit status 1.\nTraceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\n    if __name__=='__main__': main()\n                             ^^^^^^\n  File \"/app/check.py\", line 11, in main\n    subprocess.run([sys.executable,str(ROOT/'run_all.py')],cwd=ROOT,check=True,timeout=120)\n  File \"/usr/local/lib/python3.12/subprocess.py\", line 571, in run\n    raise CalledProcessError(retcode, process.args,\nsubprocess.CalledProcessError: Command '['/installed-agent/langgraph-venv/bin/python3', '/app/run_all.py']' returned non-zero exit status 1.\n"}
- LangGraph planning：None；parallel_width：None。
- 工具调用：98；最大并发：2。

Trace: `../../traces/langgraph/backup_restore_certification_spec_v4`
