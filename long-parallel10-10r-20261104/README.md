# 长并行分支10r任务集（2026-11-04）

本目录收录用户提供的10个coding任务，共30个业务组件。来源为 `SemServe-长并行分支10r任务acc有offer与无offer对照-20261104.zip`；压缩包内的310个任务文件均按原始字节保留，未修改题目、输入、业务规格、实现占位或检查程序。

## 下载与目录

- [下载原始任务ZIP](long-parallel10-10r-tasks-20261104.zip)（原始归档的英文文件名副本，内容字节完全相同）
- [浏览全部任务](tasks/)
- [任务清单](manifest.json)
- [上传前静态检查与逐文件摘要](upload-validation.json)
- [SHA-256校验表](SHA256SUMS)

ZIP解压后为10个任务目录；仓库中这些目录集中放在`tasks/`下。单题入口是`TASK.md`，实际工作区为`workspace/`。

| 任务ID | 题目 | 业务组件 |
|---|---|---|
| [operations_release_lab](tasks/operations_release_lab/TASK.md) | 运维变更与保障决策 | crews, maintenance, reserve |
| [fulfillment_release_lab](tasks/fulfillment_release_lab/TASK.md) | 履约能力与采购承诺 | loading, procurement, shipping |
| [platform_restore_lab](tasks/platform_restore_lab/TASK.md) | 平台恢复与切换验收 | journal, quorum, recovery |
| [medical_response](tasks/medical_response/TASK.md) | 应急医疗资源调度 | ambulance_windows, clinic_crews, cold_storage |
| [grid_blackstart](tasks/grid_blackstart/TASK.md) | 配电孤岛复电 | energize_jobs, grid_reserve, grid_telemetry |
| [refund_settlement](tasks/refund_settlement/TASK.md) | 区域退款清算 | ledger_recovery, liquidity_packs, refund_journal |
| [rail_renewal](tasks/rail_renewal/TASK.md) | 轨道交通更新 | rail_crews, rail_spares, track_access |
| [flood_relief](tasks/flood_relief/TASK.md) | 洪灾安置与补给 | flood_mitigation, relief_delivery, shelter_loads |
| [research_migration](tasks/research_migration/TASK.md) | 科研数据迁移 | archive_replicas, catalog_journal, dataset_restore |
| [plant_overhaul](tasks/plant_overhaul/TASK.md) | 工业产线检修 | line_shutdown, plant_crews, plant_resilience |

## 运行与检查

在独立Linux工作区中使用Python 3及标准库，按本题README、各组件SPEC.md与contract.json完成实现。每个组件包含model.py、solver.py、audit.py的待实现接口，并提供render.py、fixtures.json与check_module.py；根目录提供run_all.py与check.py。具体字段、算法边界、可修改范围和验收要求以原始任务文件为准。

```bash
cd tasks/operations_release_lab/workspace
python3 engines/maintenance/check_module.py
python3 check.py
```

这些是原压缩包自带的公开检查。该归档未提供独立的隐藏verifier目录；不要把公开通过直接等同于其他历史数据集的严格评分。本次上传不附加预设Agent DAG、Offer时机或历史执行结果，也未运行新的模型实验。

## 完整性

`.gitattributes`在本目录禁用文本换行转换，以保持原始换行和SHA-256。下载后可在本目录运行`sha256sum -c SHA256SUMS`。任务文件与ZIP均可通过upload-validation.json和manifest.json追溯至输入归档。
