# Adaptive access review engine

实现访问治理分析工具，完成例外窗口选择、复核员约束分配和策略发布依赖推演，并生成统一审计报告。

这是一个实现缺失的本地 Python 仓库。请阅读根 `check.py`、各目录的 `contract.json`、`check_module.py` 与 `inputs/`，实现全部缺失模块并运行 `python3 check.py`。不得修改 README、输入、契约、检查脚本或 `integrate.py`。

## 求解器

- `exception_windows`：在半开区间不冲突约束下最大化总价值，并按 ID 列表确定性打破平局。
- `reviewer_assignment`：在技能与容量约束下完成全量分配，依次最大化得分、最小化成本并稳定打破平局。
- `policy_rollout`：验证依赖、生成最早可执行批次，并计算按持续时间计的确定性关键路径。

每个 `engines/<name>/` 都需要实现：

- `model.py`：提供 `load_payload(path)`，读取并检查 JSON 对象；
- `solver.py`：提供 `solve(payload)`，严格遵守该目录契约中的算法和输出 schema；
- `render.py`：提供 `run(input_path, contract_path)`，调用求解器并以 UTF-8、排序键、两空格缩进写入契约指定位置。

每个目录可用 `python3 check_module.py` 做局部验证。所有求解器完成后，运行 `python3 integrate.py` 生成 `outputs/final_report.json`，最后运行 `python3 check.py`。
