# policy_decisions

输入字段为 policies, events。缺省字段沿用原题约定。

按输入顺序重放策略变更，为每个 request 原位置生成授权布尔值。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check policy_decisions
python -B component_runtime.py run policy_decisions
```
