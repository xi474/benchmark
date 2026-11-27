# C031 · LATTE 20 轮补跑 trace

[逐题 ZIP](traces/c031-rerun/latte-planning-adapted/C031.zip) · [SHA-256 清单](trace-manifest.json) · [两次尝试审计](c031-attempt-audit.json)

这次归档包含 LATTE 原生事件、进程退出探针、已保存的 stderr 文件、资源样本、请求账本和 120 份实际出站请求快照。
子进程达到 100 执行轮后以状态码 1 退出，探针无终止信号，stderr 文件为 0 字节。120 个请求全部结算。

[旧 C031 attempt](../upstream59-v21-glm53-low-20261127/traces/latte20/latte-planning-adapted/C031.zip) · [补跑前完整 trace 目录](../upstream59-v21-glm53-low-20261127/TRACE.md)
