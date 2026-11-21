# row_identities

输入字段为 txs。缺省字段沿用原题约定。

按事务、语句生成被消费旧主键的去重有序数组，I 不消耗旧主键。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check row_identities
python -B component_runtime.py run row_identities
```
