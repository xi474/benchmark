# Supply-chain assurance

修复软件供应链证据汇聚工具。独立处理依赖、容器和许可证证据，构建统一安全核心，再生成修复优先级、SBOM 摘要和合规证明。

这是一个已有接口但实现缺失的本地 Python 仓库。不得修改 `inputs/`、任何 `contract.json`、`check_module.py` 或根 `check.py`。所有 JSON 写入使用 UTF-8、稳定排序键和两空格缩进。

## 证据处理组件

- `dependencies`: 原始记录在 `inputs/dependencies.json`，规则在 `domains/dependencies/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。
- `containers`: 原始记录在 `inputs/containers.json`，规则在 `domains/containers/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。
- `licenses`: 原始记录在 `inputs/licenses.json`，规则在 `domains/licenses/contract.json`；需要补齐 `parse.py`、`normalize.py`、`analyze.py`、`render.py`，并通过该目录的 `check_module.py`。

每个证据组件公开以下函数：

- `parse.load_records(path)`：读取 JSON 数组并检查 `id/category/score/owner/tags`。
- `normalize.normalize_records(rows, contract)`：清理文本，score 按 `score * multiplier + offset` 计算并限制在 0..20，记录按 id 排序。
- `analyze.build_summary(rows, threshold)`：生成 count、score_total、high_ids、owner_scores、category_counts。
- `render.build_evidence(input_path, contract_path)`：组合 domain、records、summary；脚本入口写入契约指定 output。

三个证据 JSON 都生成以后，运行 `python3 integrate.py` 生成 `outputs/core_manifest.json`。`integrate.py` 已提供，不应修改；它会验证所有证据文件并形成唯一的统一记录集合。

## 发布视图组件

- `remediation_priority`: 规则位于 `views/remediation_priority/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。
- `sbom_summary`: 规则位于 `views/sbom_summary/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。
- `compliance_attestation`: 规则位于 `views/compliance_attestation/contract.json`；需要补齐 `filter_records.py`、`summarize.py`、`render.py`，并通过该目录的 `check_module.py`。

每个视图组件公开以下函数：

- `filter_records.select_records(core, contract)`：按 high/owner/tag 规则筛选并按 `(-score, source, id)` 排序。
- `summarize.summarize_records(rows)`：生成 count、score_total、source_counts。
- `render.build_view(core_path, contract_path)`：组合 view、filter、统计量和精简 items；脚本入口写入契约指定 output。

最后补齐 `final_report.py` 和 `run_all.py`。`run_all.py` 必须从仓库根目录依次运行组件、生成 core、运行视图、生成最终报告；任何子命令失败都应使进程失败。`final_report.py` 读取 core 与三个视图并写入 `outputs/final_report.json`。

完成后运行 `python3 check.py`。组件工作可以使用目录内的 focused check；根验收只由根执行一次。
