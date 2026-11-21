# local_regressions

输入字段为 nodes, covariance, allowed, root, max_parents。缺省字段沿用原题约定。

为每个节点及其容许的父集合计算未舍入回归系数；返回每节点一张表，以逗号分隔的升序父下标为键，空集用空字符串。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check local_regressions
python -B component_runtime.py run local_regressions
```
