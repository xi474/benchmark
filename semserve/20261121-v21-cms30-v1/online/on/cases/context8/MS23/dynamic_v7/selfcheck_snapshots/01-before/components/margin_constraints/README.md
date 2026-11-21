# margin_constraints

输入字段为 snapshots。缺省字段沿用原题约定。

为每个快照输出 [ab 与 ac 各 a 总量是否相容,按 a,c 行优先展开的 ac 配额]。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check margin_constraints
python -B component_runtime.py run margin_constraints
```
