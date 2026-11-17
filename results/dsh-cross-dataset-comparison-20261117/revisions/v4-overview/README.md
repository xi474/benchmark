# DSH跨任务集对照：同事审阅v4导读版

[先读主报告](DSH单多Agent跨任务集对照报告.md)。本版先解释五类实验的内容和目的，再列各自结论，最后展开方法、对比表和图表；同时澄清运行模式、L114两次配对重测版本、证据限制及阅读依赖，数字仍为2026-11-15—17的原153条记录和选定130条主对照。

Complex10有N原生、S禁委派、M显式至少1工作子三组；M不是仅鼓励。Mabench多需求M则鼓励自主评估，允许0–3子、不强制最低数量，实际6次全0子。R3为固定1参考子，LATTE任务为固定2子，Mabench原0/2为强制2子及运行时前置门禁。不能只看M字母就当作同一种多Agent干预。

- [逐试次模式映射](trial-condition-map.csv)、[模式定义](evidence/condition-definitions.json)、[冻结提示及来源SHA](evidence/condition-source-registry.json)。
- [主145条明细](reporting-cells145.csv)、[全153条明细](all-attempts153.csv)、[本轮8条](retest8-cells.csv)、[结构化JSON](comparison.json)。145/153为运营记录，主对照130条，名单关系见[evidence/selection-membership.json](evidence/selection-membership.json)。
- [多需求逐次证据摘录](evidence/mabench-optional-trace-extracts.json)、[强制两子工作摘录](evidence/mabench-forced-work-extracts.json)、[Mabench探索附录](审计附录-Mabench前8次.md)。摘录不是所有原生trace原件。
- 图表01/02/03提供PNG和SVG，Canvas只是需要Codex支持的可选文件。

接收者离线复算：在本目录执行`python portable_recalculate.py`，只使用本包CSV/JSON，无第三方依赖、不访问作者绝对路径、不调用模型。作者侧build_report.py/build_retest_update.py重建图表仍依赖原本机源摘要，不是同事可独立重跑实验的入口。

本包不包含原生全会话、候选仓库或镜像，不承诺重执行付费实验；缓存来自供应商usage，费用统一冻结峰价估算非账单，两个历史unknown不补0。原LATTE源码与私有MLP-PPT24不在交付中。未自动push。

## L114两行怎样读

- **L114配对重测A（原重复2·协议v3）**：沿用v3参考协议＋信用控制v2；单Agent884.5秒→多Agent412.6秒，均12/12。
- **L114配对重测B（原重复1·事务冻结v4）**：事务冻结v4＋只读分类v3.1，沿用信用控制v2；单Agent510.0秒→多Agent754.5秒，均12/12。

这是同一道L114原计划两次重复各自的整对补跑，每对含单／多Agent各一次、合计4trial，不是两道题。A/B处理失败参考的规则和实际负载不同，时间、tokens和费用不混成同协议平均值；正式API判定未变，六对合计仅作带说明的事后质量敏感性。准确来源字段见[evidence/l114-pair-protocols.json](evidence/l114-pair-protocols.json)，主报告第5节说明旧缺分、NameError、v4事务冻结及v3.1只读修复。旧交付ZIP保留；最新交付文件名含“v4导读版”。
