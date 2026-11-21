# layer_candidates

输入字段为 snapshots。缺省字段沿用原题约定。

为每个快照按 b 生成候选层数组。每层候选为 [按 a,c 行优先的计数向量,该层的中位数净分]，满足边际、禁止格和 ac 上限；按向量字典序。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check layer_candidates
python -B component_runtime.py run layer_candidates
```
