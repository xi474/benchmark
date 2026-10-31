# Codex / OpenCode 反例验证行为：源码与 trace 证据

[阅读中文完整分析报告](codex-opencode-counterexample-review.zh-CN.md)。报告的源码、trace、trial 结果及生成脚本均在本目录，所有引用可在 GitHub 打开，无需作者的本地路径。

- [源码摘录](source-excerpts.md)：16 个带行号来源。
- [原始证据与哈希](evidence.json)：32 份 trace、3 个详细案例。
- [运行时脚本及算法索引](generated-tests/README.md)：工具调用中生成的各版本。
- [反例独立核算](oracle-witness.json)。
- [版本来源](version-provenance.json)。
- [第三方声明](THIRD_PARTY_NOTICES.md)。

仅发布报告引用的公开实验材料；没有复制 hidden verifier、账户数据库或凭据。源码/trace 是审计快照；文中 `/app` 和 `/tmp` 是被测容器的运行时路径。

下载此完整目录后，运行 `python extract_evidence.py` 可基于 snapshots 离线重新抽取证据，输出位于 `_recheck/`。不调用模型或执行历史候选。
