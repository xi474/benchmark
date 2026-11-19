# Capstone Benchmark v1.0.0 中难题发布清单

冻结日期为 2026-11-19。主集共 **87 题**，其中 **中档 42 题、难档 45 题**。每题都有同一版本的五次有效成绩，题面和判分器沿用相应批次冻结的文件。

| 主集来源批次 | 中 | 难 | 合计 |
|---|---:|---:|---:|
| C007 加强版 | 0 | 1 | 1 |
| C31 本地改编 | 4 | 11 | 15 |
| C69 中已五测的29题 | 3 | 1 | 4 |
| Medium26 保留20题 | 0 | 20 | 20 |
| Mixed16 精确规格 | 8 | 7 | 15 |
| N30 盲编排 | 4 | 0 | 4 |
| 并行候选五测 | 20 | 3 | 23 |
| 独立六题核心版 | 3 | 2 | 5 |

[下载 87 题完整 ZIP](https://github.com/xi474/benchmark/raw/refs/heads/release/capstone-benchmark-v1.0.0/capstone-benchmark-87-v1.0.0.zip) · [浏览题包](tasks/) · [下载文件校验值](https://github.com/xi474/benchmark/blob/release/capstone-benchmark-v1.0.0/DOWNLOAD-SHA256.txt)

## 来源如何标注

| 主集来源关系 | 中 | 难 | 合计 |
|---|---:|---:|---:|
| 公开上游改编 | 14 | 35 | 49 |
| 我们自创 | 28 | 10 | 38 |

主集的 38 道“我们自创”包括直接设计的 19 题，以及根据我们自建的 DAG300 题库改编的 19 题。DAG300 改编题逐题保留原题族 ID、仓库链接和溯源记录。公开上游改编题逐题标注原 benchmark、原题 ID 与链接，多来源任务分别列出。

## 难度与版本

校准使用 Terminus 2、DeepSeek V4 Pro 普通模式。五次中 0–1 次整题通过为难，2–3 次为中，4–5 次为易。独立六题核心版使用其正式核心整题指标，独立稳健性另计。各批次的评分器、原始 reward 上限、输入规模及环境有差异，跨批次保留原口径。全部逐轮数据见 catalog.json 和 evidence/。

主集按独立题目和发布版本去重，保留原有评审决定。早期为“只补中档”而筛掉的 F04、Q10、S01 已有五次难档记录，本版按中难兼收纳入。档位描述当前基线下的交付难度。旧 Medium26 的部分失败受通用边界影响，逐题列出剔除非有限数后的历史诊断；该诊断不改变五次实测分。


## 主集逐题清单

| 题号 | 题目 | 档 | 通过 | 来源 | 来源题号 |
|---|---|---:|---:|---|---|
| [C007](tasks/C007/) | 多渠道实体识别与家庭冲突消解 | 难 | 0/5 | 公开上游改编 · Terminal-Bench 4.1 | [telecom-entity-resolution](https://github.com/harbor-framework/terminal-bench/tree/4070d6cef56a7d20cb5dc98d5e10ada88a6b9440/tasks/telecom-entity-resolution) |
| [C008](tasks/C008/) | 跨租户有效期合并的匿名化 | 中 | 3/5 | 公开上游改编 · Terminal-Bench 4.1 | [data-anonymization](https://github.com/harbor-framework/terminal-bench/tree/4070d6cef56a7d20cb5dc98d5e10ada88a6b9440/tasks/data-anonymization) |
| [C009](tasks/C009/) | 部分可见班次中的不可逆运输调度 | 中 | 3/5 | 公开上游改编 · Terminal-Bench 4.1 | [freight-dispatch-shift](https://github.com/harbor-framework/terminal-bench/tree/4070d6cef56a7d20cb5dc98d5e10ada88a6b9440/tasks/freight-dispatch-shift) |
| [C011](tasks/C011/) | ERP、MES、WMS联合滚动生产计划 | 中 | 2/5 | 公开上游改编 · Terminal-Bench 4.1 | [production-planning](https://github.com/harbor-framework/terminal-bench/tree/4070d6cef56a7d20cb5dc98d5e10ada88a6b9440/tasks/production-planning) |
| [C017](tasks/C017/) | 多入口线索提交与历史账本核对 | 难 | 1/5 | 公开上游改编 · Terminal-Bench 4.1 | [react-lead-form](https://github.com/harbor-framework/terminal-bench/tree/4070d6cef56a7d20cb5dc98d5e10ada88a6b9440/tasks/react-lead-form) |
| [C031](tasks/C031/) | 交互终端的按键、回显与进程生命周期 | 难 | 0/5 | 公开上游改编 · Terminal-Bench 2.0 | [headless-terminal](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6/headless-terminal) |
| [C033](tasks/C033/) | MIPS装载、指令与系统调用模拟 | 难 | 0/5 | 公开上游改编 · Terminal-Bench 2.0 | [make-mips-interpreter](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6/make-mips-interpreter) |
| [C039](tasks/C039/) | 带结构先验的因果图学习与干预 | 中 | 2/5 | 公开上游改编 · Terminal-Bench 2.0 | [bn-fit-modify](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6/bn-fit-modify) |
| [C049](tasks/C049/) | 流水并行训练的微批次与反向调度 | 难 | 0/5 | 公开上游改编 · Terminal-Bench 2.0 | [torch-pipeline-parallelism](https://github.com/harbor-framework/terminal-bench-2/tree/2fd12b88aafdd04a52c298e3940bcb189f9766d6/torch-pipeline-parallelism) |
| [C058](tasks/C058/) | 多主机任务迭代与处理器通知 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_ansible__ansible-d6d2251929c84c3aa883bad7db0f19cc9ff0339e-v30a923fb5c164d6cd18280c02422f75e611e8fb2](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C062](tasks/C062/) | 多存储后端轮询的取消与关闭 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_flipt-io__flipt-dbe263961b187e1c5d7fe34c65b000985a2da5a0](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C067](tasks/C067/) | 逐请求授权与临时凭据缓存解耦 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_gravitational__teleport-3fa6904377c006497169945428e8197158667910-v626ec2a48416b10a88641359a169d99e935ff037](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C068](tasks/C068/) | 共享在途加载、取消与TTL缓存 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_gravitational__teleport-78b0d8c72637df1129fb6ff84fc49ef4b5ab1288](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C069](tasks/C069/) | 会话续期中的角色、资源与用户特征 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_gravitational__teleport-e6d86299a855687b21970504fbf06f52a8f80c74-vce94f93ad1030e3136852817f2423c1b3ac37bc4](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C077](tasks/C077/) | 邮箱变更、延迟刷新与陈旧响应 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_protonmail__webclients-e65cc5f33719e02e1c378146fb981d27bc24bdf4](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C079](tasks/C079/) | 加密块验证、重试与文件摘要一致性 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro | [instance_protonmail__webclients-5d2576632037d655c3b6a28e98cd157f7e9a5ce1](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C055](tasks/C055/) | 多来源 YAML 注记、密文与模板读回 | 难 | 1/5 | 公开上游改编 · SWE-bench Pro | [instance_ansible__ansible-1c06c46cc14324df35ac4f39a45fb3ccd602195d-v0f01c69f1e2528b935359cfe578530722bca2c59](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C056](tasks/C056/) | 带依赖批次的单次委派与重试回放 | 中 | 2/5 | 公开上游改编 · SWE-bench Pro | [instance_ansible__ansible-42355d181a11b51ebfc56f6f4b3d9c74e01cb13b-v1055803c3a812189a1133297f7f5468579283f86](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C066](tasks/C066/) | 逻辑复制的事务重放与主键交换 | 中 | 3/5 | 公开上游改编 · SWE-bench Pro | [instance_gravitational__teleport-005dcb16bacc6a5d5890c4cd302ccfd4298e275d-vee9b09fb20c43af7e520f57e9239bbcf46b7113d](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [C074](tasks/C074/) | 可中断的多挂载音乐库同步 | 中 | 3/5 | 公开上游改编 · SWE-bench Pro | [instance_navidrome__navidrome-3853c3318f67b41a9e4cb768618315ff77846fdb](https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro/tree/2d52cb3df914a3fcf80c7f66738b3a88ae37fc50) |
| [MP01](tasks/MP01/) | 可关闭成员的硬/软加权投票 | 难 | 0/5 | 公开上游改编 · SWE-bench Verified | [scikit-learn__scikit-learn-13779](https://github.com/scikit-learn/scikit-learn/pull/13779) |
| [MP02](tasks/MP02/) | 单变化轴的数据分片拼接 | 难 | 0/5 | 公开上游改编 · SWE-bench Verified | [pydata__xarray-3151](https://github.com/pydata/xarray/pull/3151) |
| [MP03](tasks/MP03/) | 三种挂载格式的离线事实归并 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf/instruction.md) |
| [MP05](tasks/MP05/) | 跨应用候选并集与相处时长排名 | 难 | 0/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_23_8pzn4g](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=34) |
| [MP06](tasks/MP06/) | 取消日程后多渠道通知 | 难 | 0/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_24_lr8en2](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=64) |
| [MP07](tasks/MP07/) | 附件发送后归档与独立清理 | 难 | 1/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_21_2m6akl](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=69) |
| [MP12](tasks/MP12/) | 下载目录归档、邮件清理与目标回复 | 难 | 0/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_28_nfnpyk](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=76) |
| [MP13](tasks/MP13/) | 聚合特征的行键保真与特征合并 | 难 | 1/5 | 公开上游改编 · SWE-bench Verified | [scikit-learn__scikit-learn-25747](https://github.com/scikit-learn/scikit-learn/pull/25747) |
| [MP14](tasks/MP14/) | 异常链的可移植序列化与报告 | 难 | 0/5 | 公开上游改编 · SWE-bench Verified | [pytest-dev__pytest-5787](https://github.com/pytest-dev/pytest/pull/5787) |
| [MP15](tasks/MP15/) | 普通引用、注解和类型注释的导入分析 | 难 | 0/5 | 公开上游改编 · SWE-bench Verified | [pylint-dev__pylint-4604](https://github.com/pylint-dev/pylint/pull/4604) |
| [MP16](tasks/MP16/) | API 文档的签名、参数与继承信息聚合 | 难 | 0/5 | 公开上游改编 · SWE-bench Verified | [sphinx-doc__sphinx-7748](https://github.com/sphinx-doc/sphinx/pull/7748)、[sphinx-doc__sphinx-9230](https://github.com/sphinx-doc/sphinx/pull/9230)、[sphinx-doc__sphinx-8548](https://github.com/sphinx-doc/sphinx/pull/8548) |
| [MP17](tasks/MP17/) | 文本、内联内容和文件的 multipart 组装 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86/instruction.md) |
| [MP18](tasks/MP18/) | 集合文件清单的指令选择与归档元数据 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_ansible__ansible-d2f80991180337e2be23d6883064a67dcbaeb662-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-d2f80991180337e2be23d6883064a67dcbaeb662-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5/instruction.md) |
| [MP19](tasks/MP19/) | Python 支持模块发现与可重复 ZIP 载荷 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_ansible__ansible-c616e54a6e23fa5616a1d56d243f69576164ef9b-v1055803c3a812189a1133297f7f5468579283f86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-c616e54a6e23fa5616a1d56d243f69576164ef9b-v1055803c3a812189a1133297f7f5468579283f86/instruction.md) |
| [MP20](tasks/MP20/) | 特性配置的模式、附件与引用一致性 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_flipt-io__flipt-c8d71ad7ea98d97546f01cce4ccb451dbcf37d3b](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_flipt-io__flipt-c8d71ad7ea98d97546f01cce4ccb451dbcf37d3b/instruction.md)、[instance_flipt-io__flipt-e91615cf07966da41756017a7d571f9fc0fdbe80](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_flipt-io__flipt-e91615cf07966da41756017a7d571f9fc0fdbe80/instruction.md) |
| [MP21](tasks/MP21/) | 播放列表重写、条件查询与 M3U 导出 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_navidrome__navidrome-d21932bd1b2379b0ebca2d19e5d8bae91040268a](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_navidrome__navidrome-d21932bd1b2379b0ebca2d19e5d8bae91040268a/instruction.md)、[instance_navidrome__navidrome-28389fb05e1523564dfc61fa43ed8eb8a10f938c](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_navidrome__navidrome-28389fb05e1523564dfc61fa43ed8eb8a10f938c/instruction.md) |
| [MP22](tasks/MP22/) | MARC 作者标题、语言和主题导入 | 难 | 0/5 | 公开上游改编 · SWE-bench Pro V2 | [instance_internetarchive__openlibrary-111347e9583372e8ef91c82e0612ea437ae3a9c9-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-111347e9583372e8ef91c82e0612ea437ae3a9c9-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59/instruction.md)、[instance_internetarchive__openlibrary-3c48b4bb782189e0858e6c3fc7956046cf3e1cfb-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-3c48b4bb782189e0858e6c3fc7956046cf3e1cfb-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59/instruction.md)、[instance_internetarchive__openlibrary-7c8dc180281491ccaa1b4b43518506323750d1e4-v298a7a812ceed28c4c18355a091f1b268fe56d86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-7c8dc180281491ccaa1b4b43518506323750d1e4-v298a7a812ceed28c4c18355a091f1b268fe56d86/instruction.md) |
| [MP23](tasks/MP23/) | 受目录容量限制的可逆文件重分片 | 难 | 0/5 | 公开上游改编 · Terminal-Bench | [reshard-c4-data](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/reshard-c4-data/instruction.md) |
| [MP25](tasks/MP25/) | 文本票据分类、金额提取与归档汇总 | 难 | 0/5 | 公开上游改编 · Terminal-Bench | [financial-document-processor](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/financial-document-processor/instruction.md) |
| [MP26](tasks/MP26/) | 每日晚餐提醒的去重、冲突取消与通知 | 难 | 0/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_25_642cr1](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=86) |
| [MX-api_deprecation_campaign_spec_v4](tasks/MX-api_deprecation_campaign_spec_v4/) | API 下线管理 | 中 | 3/5 | 我们自创 · Mixed16 | api_deprecation_campaign_spec_v4 |
| [MX-artifact_provenance_release_spec_v4](tasks/MX-artifact_provenance_release_spec_v4/) | 制品溯源发布 | 中 | 2/5 | 我们自创 · Mixed16 | artifact_provenance_release_spec_v4 |
| [MX-backup_restore_certification_spec_v4](tasks/MX-backup_restore_certification_spec_v4/) | 备份恢复认证 | 中 | 3/5 | 我们自创 · Mixed16 | backup_restore_certification_spec_v4 |
| [MX-batch_scheduler_transition_spec_v4](tasks/MX-batch_scheduler_transition_spec_v4/) | 批处理调度迁移 | 难 | 0/5 | 我们自创 · Mixed16 | batch_scheduler_transition_spec_v4 |
| [MX-certificate_rotation_readiness_spec_v4](tasks/MX-certificate_rotation_readiness_spec_v4/) | 证书轮换准备 | 中 | 2/5 | 我们自创 · Mixed16 | certificate_rotation_readiness_spec_v4 |
| [MX-edge_fleet_rollout_spec_v4](tasks/MX-edge_fleet_rollout_spec_v4/) | 边缘设备灰度发布 | 难 | 0/5 | 我们自创 · Mixed16 | edge_fleet_rollout_spec_v4 |
| [MX-identity_federation_transition_spec_v4](tasks/MX-identity_federation_transition_spec_v4/) | 身份联邦迁移 | 难 | 1/5 | 我们自创 · Mixed16 | identity_federation_transition_spec_v4 |
| [MX-network_policy_convergence_spec_v4](tasks/MX-network_policy_convergence_spec_v4/) | 网络策略收敛 | 中 | 2/5 | 我们自创 · Mixed16 | network_policy_convergence_spec_v4 |
| [MX-observability_retention_upgrade_spec_v4](tasks/MX-observability_retention_upgrade_spec_v4/) | 可观测数据保留升级 | 中 | 2/5 | 我们自创 · Mixed16 | observability_retention_upgrade_spec_v4 |
| [MX-regional_failover_readiness_spec_v4](tasks/MX-regional_failover_readiness_spec_v4/) | 跨区域故障切换 | 难 | 1/5 | 我们自创 · Mixed16 | regional_failover_readiness_spec_v4 |
| [MX-search_index_rebuild_spec_v4](tasks/MX-search_index_rebuild_spec_v4/) | 搜索索引重建 | 难 | 1/5 | 我们自创 · Mixed16 | search_index_rebuild_spec_v4 |
| [MX-storage_tiering_migration_spec_v4](tasks/MX-storage_tiering_migration_spec_v4/) | 存储分层迁移 | 中 | 3/5 | 我们自创 · Mixed16 | storage_tiering_migration_spec_v4 |
| [MX-streaming_checkpoint_recovery_spec_v4](tasks/MX-streaming_checkpoint_recovery_spec_v4/) | 流处理检查点恢复 | 难 | 1/5 | 我们自创 · Mixed16 | streaming_checkpoint_recovery_spec_v4 |
| [MX-tenant_quota_rebalance_spec_v4](tasks/MX-tenant_quota_rebalance_spec_v4/) | 租户配额再平衡 | 难 | 1/5 | 我们自创 · Mixed16 | tenant_quota_rebalance_spec_v4 |
| [MX-warehouse_cutover_assurance_spec_v4](tasks/MX-warehouse_cutover_assurance_spec_v4/) | 数仓切换保障 | 中 | 3/5 | 我们自创 · Mixed16 | warehouse_cutover_assurance_spec_v4 |
| [N11](tasks/N11/) | 零块保形的分块矩阵连乘 | 中 | 2/5 | 公开上游改编 · SWE-bench Verified | [sympy__sympy-17630](https://github.com/sympy/sympy/pull/17630) |
| [N17](tasks/N17/) | 模板配置依赖与最小更新集合 | 中 | 3/5 | 公开上游改编 · SWE-bench Pro | [instance_qutebrowser__qutebrowser-35168ade46184d7e5b91dfa04ca42fe2abd82717-v363c8a7e5ccdf6968fc7ab84a2053ac78036691d](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_qutebrowser__qutebrowser-35168ade46184d7e5b91dfa04ca42fe2abd82717-v363c8a7e5ccdf6968fc7ab84a2053ac78036691d/instruction.md) |
| [N22](tasks/N22/) | Git 遗失对象恢复与彻底清理 | 中 | 2/5 | 公开上游改编 · Terminal-Bench 2.0 | [git-leak-recovery](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/git-leak-recovery/instruction.md) |
| [N24](tasks/N24/) | COBOL 定长交易文件的 Python 等价迁移 | 中 | 3/5 | 公开上游改编 · Terminal-Bench 2.0 | [cobol-modernization](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/cobol-modernization/instruction.md) |
| [E112](tasks/E112/) | 共享道路与有资格避难所的全局撤离 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new112-wildfire-evacuation-grid](https://github.com/horacezoe/DagAndCodingBench) |
| [F04](tasks/F04/) | 双版本排印索引 | 难 | 1/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300-new48-document-pagination](https://github.com/horacezoe/DagAndCodingBench) |
| [F15](tasks/F15/) | 分隔平面的最低通行费面积 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new66-polygon-overlay](https://github.com/horacezoe/DagAndCodingBench) |
| [F18](tasks/F18/) | 带回流与停滞分支的交付时间 | 中 | 3/5 | 我们自创 · Capstone 原创 | capstone-original-conditional-delivery |
| [F20](tasks/F20/) | 生产循环的可持续单位产出 | 中 | 2/5 | 我们自创 · Capstone 原创 | capstone-original-sustainable-yield |
| [I06](tasks/I06/) | 共享校准与整数装配的中等规模对照 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new140-cad-tolerance-stackup](https://github.com/horacezoe/DagAndCodingBench) |
| [K54](tasks/K54/) | 完整CFG的最优溢出与加权phi合并 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300-new53-register-allocation](https://github.com/horacezoe/DagAndCodingBench) |
| [K64](tasks/K64/) | 包依赖闭包与冲突的中等规模对照 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300-new63-package-constraint-solver](https://github.com/horacezoe/DagAndCodingBench) |
| [L114](tasks/L114/) | 编码子空间与前置交付的全局地面链路 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new113-spacecraft-groundlink-budget](https://github.com/horacezoe/DagAndCodingBench) |
| [M103](tasks/M103/) | 端口驻留与储能的全时域恢复 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new102-microgrid-restoration](https://github.com/horacezoe/DagAndCodingBench) |
| [Q08](tasks/Q08/) | 碎片质谱的一对一峰匹配 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new161-peptide-mass-matching](https://github.com/horacezoe/DagAndCodingBench) |
| [Q10](tasks/Q10/) | 票据流转和临时票核账 | 难 | 0/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new170-precinct-ballot-reconciliation](https://github.com/horacezoe/DagAndCodingBench) |
| [Q20](tasks/Q20/) | 海流场反演与漂流轨迹 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new199-ocean-current-drifter-inversion](https://github.com/horacezoe/DagAndCodingBench) |
| [S01](tasks/S01/) | 环形遥测包的软判决 | 难 | 1/5 | 我们自创 · Capstone 原创 | capstone-original-circular-telemetry |
| [S02](tasks/S02/) | 祖先性状变化的全局支持度 | 中 | 2/5 | 我们自创 · Capstone 原创 | capstone-original-ancestral-support |
| [S129](tasks/S129/) | 重试与逆依赖回滚的最短补偿事务 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new129-saga-compensation-planner](https://github.com/horacezoe/DagAndCodingBench) |
| [U109](tasks/U109/) | 组合拍卖全部最优分配与反事实支付 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new109-combinatorial-auction-clearing](https://github.com/horacezoe/DagAndCodingBench) |
| [V163](tasks/V163/) | 共享建设的跨季节生态廊道 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new163-ecological-corridor-planning](https://github.com/horacezoe/DagAndCodingBench) |
| [W07](tasks/W07/) | 多版本事务的传播隔离 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new43-mvcc-serializability](https://github.com/horacezoe/DagAndCodingBench) |
| [W11](tasks/W11/) | 共享时钟下的真实时序余量 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new68-static-timing](https://github.com/horacezoe/DagAndCodingBench) |
| [X13](tasks/X13/) | 跨链审查场次的最优排程 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new62-crdt-reconciliation](https://github.com/horacezoe/DagAndCodingBench) |
| [Y193](tasks/Y193/) | 共享堆位与多吊机的全局取货 | 中 | 3/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300new193-port-container-yard](https://github.com/horacezoe/DagAndCodingBench) |
| [Z10](tasks/Z10/) | 配额申诉后各项分配的变动频率 | 中 | 2/5 | 我们自创 · DagAndCodingBench / DAG300 | [dag300-new85-survey-raking](https://github.com/horacezoe/DagAndCodingBench) |
| [MP04](tasks/MP04/) | 多格式用户合并与完整冲突报告 | 难 | 1/5 | 公开上游改编 · Terminal-Bench | [multi-source-data-merger](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/multi-source-data-merger/instruction.md) |
| [MP08](tasks/MP08/) | 节日照片迁移后发送与缺失报告 | 中 | 2/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_28_wy635e](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=110) |
| [MP09](tasks/MP09/) | 两场座谈会、群邀请与物资采购 | 中 | 2/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_29_8hgfug](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=65) |
| [MP10](tasks/MP10/) | 晚宴计划、联系人定位与餐具采购 | 中 | 3/5 | 公开上游改编 · GAIA2 公开 mini / validation | [scenario_universe_26_135a24](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=66) |
| [MP24](tasks/MP24/) | 大学任职、在读人数与国家集合查询 | 难 | 1/5 | 公开上游改编 · Terminal-Bench | [sparql-university](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/sparql-university/instruction.md) |

## 会影响解读的逐题说明

- **C007**　初版 5/5，入选版本为模型首次运行前冻结的加强版 2.0.1。
- **MP01**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 4/5。
- **MP02**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 0/5。
- **MP03**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 3/5。
- **MP05**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 4/5。
- **MP06**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 2/5。
- **MP07**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 2/5。
- **MP12**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 5/5。
- **MP13**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 2/5。
- **MP14**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 2/5。
- **MP15**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 1/5。
- **MP16**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 5/5。
- **MP17**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 4/5。
- **MP18**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 4/5。
- **MP19**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 3/5。
- **MP20**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 5/5。
- **MP21**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 2/5。
- **MP22**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 0/5。
- **MP23**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 3/5。
- **MP25**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 3/5。
- **MP26**　历史严格验收包含非有限数等通用检查。仅排除非有限数后的诊断成功数为 0/5。
- **F04**　此前筛选只接纳中档。本次按原五次严格实测纳入难档，核心通过 44/50。
- **Q10**　此前筛选只接纳中档。五轮均在同一业务用例 A/analysis/7 失分，核心合计 35/40；按公开记账规则独立重算八个核心样例，均与金标一致。
- **S01**　四次失败均在较长遥测包上超时。原规格未明示最大环长，难档与输入规模及预算有关。
- **MP04**　独立稳健性检查照常记录，只用核心整题通过次数定档。
- **MP08**　独立稳健性检查照常记录，只用核心整题通过次数定档。
- **MP09**　独立稳健性检查照常记录，只用核心整题通过次数定档。
- **MP10**　独立稳健性检查照常记录，只用核心整题通过次数定档。
- **MP24**　独立稳健性检查照常记录，只用核心整题通过次数定档。

## 如何使用题包

解压后把 tasks/ 下的单题目录交给 Harbor。每个目录保留原 instruction.md、task.toml、environment/ 和 tests/。环境依赖见 IMAGES.md。题包内的拉起方式、磁盘资源和镜像沿用该次历史校准配置；运行时把 agent 工作区与 tests/、evidence/ 分离。

例如，在已有相应镜像的 Harbor 0.24.0 环境中，空代理烟测可执行如下命令。

```sh
harbor run --path tasks/C056 --agent nop
```

发布包校验覆盖历史冻结文件的逐文件字节、五轮原始评分与归档完整性。本次整理未为发布主集重新运行付费模型。

## 发布附录

[附录 A · 构建批次、日期与六个 harness 的历史运行覆盖](附录A-构建批次与六Harness历史覆盖.md) · [逐题表（TSV）](附录A-构建批次与六Harness历史覆盖.tsv) · [运行凭据（JSON）](附录A-构建批次与六Harness历史覆盖.json)

## 公开版归档说明

发布时清理了 35 份历史冒烟测试报告和 5 份历史验收报告中的本机用户路径，并更新了关联的归档校验值。435 份基线评分已逐文件与冻结记录核对。修改路径及前后 SHA-256 见[发布记录](publication-metadata.json)。
