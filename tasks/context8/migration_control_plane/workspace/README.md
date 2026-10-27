# Migration control plane

完成迁移控制面工具链。分别核验 schema、数据质量和回滚保障，生成统一迁移核心，再输出执行波次、风险矩阵和恢复演练包。

这是一个已有接口但实现缺失的本地 Python 仓库。不得修改 `inputs/`、任何 `contract.json`、`check_module.py` 或根 `check.py`。所有 JSON 写入使用 UTF-8、稳定排序键和两空格缩进。

## 证据处理组件

- `schema`: 原始记录在 `inputs/schema.json`，规则在 `domains/schema/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。
- `data_quality`: 原始记录在 `inputs/data_quality.json`，规则在 `domains/data_quality/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。
- `rollback`: 原始记录在 `inputs/rollback.json`，规则在 `domains/rollback/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。

每个证据组件公开以下函数：

- `parse.load_records(path)`：读取 JSON 数组并检查 `id/category/score/owner/tags`。
- `normalize.normalize_records(rows, contract)`：清理文本，score 按 `score * multiplier + offset` 计算并限制在 0..20，记录按 id 排序。
- `analyze.build_summary(rows, threshold)`：生成 count、score_total、high_ids、owner_scores、category_counts。
- `render.build_evidence(input_path, contract_path)`：组合 domain、records、summary；脚本入口写入契约指定 output。

三个证据 JSON 都生成以后，运行 `python3 integrate.py` 生成 `outputs/core_manifest.json`。`integrate.py` 已提供，不应修改；它会验证所有证据文件并形成唯一的统一记录集合。

## 发布视图组件

- `execution_waves`: 规则位于 `views/execution_waves/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。
- `risk_matrix`: 规则位于 `views/risk_matrix/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。
- `recovery_drill`: 规则位于 `views/recovery_drill/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。

每个视图组件公开以下函数：

- `filter_records.select_records(core, contract)`：按 high/owner/tag 规则筛选并按 `(-score, source, id)` 排序。
- `summarize.summarize_records(rows)`：生成 count、score_total、source_counts。
- `render.build_view(core_path, contract_path)`：组合 view、filter、统计量和精简 items；脚本入口写入契约指定 output。

最后补齐 `final_report.py` 和 `run_all.py`。`run_all.py` 必须从仓库根目录依次运行组件、生成 core、运行视图、生成最终报告；任何子命令失败都应使进程失败。`final_report.py` 读取 core 与三个视图并写入 `outputs/final_report.json`。

完成后运行 `python3 check.py`。组件工作可以使用目录内的 focused check；根验收只由根执行一次。
