# DeepSeek V4 Pro 普通模式 reward-v2 七 Harness 结果

基线共392个唯一题位，每个Harness包含原14题、mixed16-v4的16题、Medium26的26题。LATTE四次独立补跑另列附表，原baseline保留。

| Harness | 数据集 | 题位 | API有效题数 | API微平均 | API宏平均 | 平均e2e秒 | 输入tokens已知部分 | 输出tokens已知部分 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| codex | medium26 | 26 | 26 | 88.32% | 87.53% | 1504.06 | 75083710 | 2181541 |
| codex | mixed16-v4 | 16 | 16 | 93.58% | 93.64% | 1240.67 | 54837705 | 1645591 |
| codex | original14 | 14 | 0 | 不适用 | 不适用 | 310.08 | 4913328 | 238099 |
| dsh | medium26 | 26 | 26 | 81.49% | 81.71% | 640.04 | 27671335 | 888244 |
| dsh | mixed16-v4 | 16 | 16 | 97.12% | 96.94% | 526.66 | 25055931 | 612325 |
| dsh | original14 | 14 | 0 | 不适用 | 不适用 | 186.20 | 3982310 | 134330 |
| langgraph | medium26 | 26 | 26 | 44.01% | 43.12% | 602.44 | 12570418 | 830123 |
| langgraph | mixed16-v4 | 16 | 16 | 41.59% | 36.16% | 465.20 | 10174560 | 549521 |
| langgraph | original14 | 14 | 0 | 不适用 | 不适用 | 279.40 | 3794215 | 242384 |
| latte-planning-adapted | medium26 | 26 | 22 | 18.07% | 20.77% | 379.93 | 13685736 | 348653 |
| latte-planning-adapted | mixed16-v4 | 16 | 12 | 36.71% | 39.84% | 592.48 | 14936456 | 368072 |
| latte-planning-adapted | original14 | 14 | 0 | 不适用 | 不适用 | 264.87 | 4672342 | 187658 |
| nanobot | medium26 | 26 | 26 | 76.78% | 77.06% | 927.59 | 51651572 | 911741 |
| nanobot | mixed16-v4 | 16 | 16 | 93.14% | 91.18% | 657.60 | 44410414 | 678166 |
| nanobot | original14 | 14 | 0 | 不适用 | 不适用 | 320.89 | 7259095 | 150549 |
| opencode | medium26 | 26 | 26 | 29.14% | 31.49% | 282.06 | 6181407 | 245344 |
| opencode | mixed16-v4 | 16 | 16 | 53.10% | 59.70% | 279.54 | 10477691 | 259792 |
| opencode | original14 | 14 | 0 | 不适用 | 不适用 | 166.48 | 3478062 | 92372 |
| roma | medium26 | 26 | 25 | 9.53% | 10.45% | 375.20 | 51895781 | 809443 |
| roma | mixed16-v4 | 16 | 14 | 1.49% | 2.04% | 280.07 | 24685416 | 445850 |
| roma | original14 | 14 | 0 | 不适用 | 不适用 | 427.42 | 32357032 | 464717 |

api_accuracy为verifier中api/检查通过数除以总数。原14题无api/分母，另列focused/通过率。无效提交、预算截断与基础设施证据失败保留原始检查数，可比较API比率为null。有效的超时、输出上限和Harbor汇总异常评分保留异常标签。

e2e从Harbor trial的started_at到finished_at，包含环境准备、Agent执行和verifier。分阶段时间另列。批次包含5/8并发及ROMA单Harbor/HTTP4，时间属于各自资源条件下的观测，不能直接归因于Harness本身。
tokens来自去重后的实际上游结算记录。缓存命中tokens为输入的子集。未知请求保留未知，完整token总量为null，已结算部分另列。费用为注册峰价或原账本估算，invoice未观测。
资源采用task-container采样。工具并发仅在执行边界可配对时报告。Agent定义、递归Solve实例、委派计数按源监控保留。ROMA原30题使用JSON指令v1传输适配，Medium26沿用早期C0 JSON-object条件。LATTE为planning-adapted。
self-check-loops.csv记录失败后分析、修复和复验的关联窗口。观察窗口与执行时间分别列出，窗口可能重叠。缺失span、不可比时钟和纯自检增量成本保留null。

ROMA原30题含24个普通scored、1个scored_with_harbor_summary_error、4个预算跳过和1个证据失败；Medium26为25个scored加1个预算跳过。

| LATTE独立补跑任务 | 分类 | reward / max | API通过数 / 总数 | API准确率 |
|---|---|---:|---:|---:|
| hard/artifact_provenance_release_spec_v4 | scored | 1.529412 / 3.0 | 19 / 37 | 51.35% |
| hard/batch_scheduler_transition_spec_v4 | invalid_submission | 0.0 / 3.0 | 0 / 21 | 不适用 |
| hard/identity_federation_transition_spec_v4 | scored | 2.4 / 3.0 | 23 / 27 | 85.19% |
| hard/tenant_quota_rebalance_spec_v4 | scored | 2.172414 / 3.0 | 17 / 21 | 80.95% |

中断修复涉及ROMA JSON模式提示、Docker退出后的隔离续跑、Harbor临时目录尾部下划线引发的汇总打印异常，以及LATTE四题唯一ID误比较26的门禁。传输IncompleteRead用量未知和输入token发送前预算截断均已隔离留证，随后继续队列。
历史ROMA R6 HTTP400、R7 Docker中断、LATTE R3 HTTP402各有1次未知用量，历史Codex29 HTTP402用量也未知，跨批费用总账仍不完整。

发布包仅含结构化指标、公开任务标识、证据SHA256和可移植定位符。原始日志、提示、工具输出、私有数据、凭据和LATTE源码均未包含。

普通模式在Chat Completions记录中为thinking.type=disabled，在Responses记录中为reasoning.effort=none。导出程序分别校验这两种实际请求口径。

文件索引如下。

- [逐题全指标392行](cells-392.csv)
- [21组汇总指标](summary-21.csv)
- [mixed16-v4逐任务API通过率](api-task-matrix-mixed16-v4.csv)
- [Medium26逐任务API通过率](api-task-matrix-medium26.csv)
- [LATTE四次独立补跑](latte-independent-repeats-4.csv)
- [自检闭环关联窗口](self-check-loops.csv)
- [结构化完整指标](results.json)
- [证据与发布文件指纹](audit.json)
- [离线导出器](scripts/export_reward_v2_metrics.py)
- [发布包校验器](scripts/validate_release.py)

下载结果后可在发布目录运行 python scripts/validate_release.py，核验文件SHA256、392题位唯一性、API微/宏平均及token完整性。原始实验数据保存在本地，凭证指纹支持持有原件时复核。复算导出需要原始outputs目录和带scripts/aggregate_verify_api_accuracy.py的工具目录，使用export_reward_v2_metrics.py的三个命名参数指定输入及新输出目录。

原始trial的source_locator为相对于本地outputs的可移植索引，GitHub发布包提供对应SHA256。每个题位的e2e包含其环境与verifier开销，未替失败attempt计作成功运行。异常、跳过和invalid_submission在CSV中保持分类。

运行时multi-agent专项审计已补充，见 [证据矩阵与口径](MULTIAGENT.md)、[逐题审计及事件指纹](runtime-multiagent-audit.json) 与 [离线复算脚本](scripts/audit_runtime_multiagent.py)。
