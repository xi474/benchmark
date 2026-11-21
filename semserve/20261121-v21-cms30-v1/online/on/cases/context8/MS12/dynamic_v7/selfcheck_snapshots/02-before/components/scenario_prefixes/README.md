# scenario_prefixes

输入字段为 scenarios。缺省字段沿用原题约定。

输出 [信号历史,该完整叶的权重或 null]，去重生成所有非空前缀，按历史字典序排列。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check scenario_prefixes
python -B component_runtime.py run scenario_prefixes
```
