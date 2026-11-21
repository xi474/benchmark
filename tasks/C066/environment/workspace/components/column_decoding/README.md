# column_decoding

输入字段为 txs。缺省字段沿用原题约定。

按事务、语句、行变更生成已解码的列映射。D 用空对象；类型错误用 null，使整合端按事务回滚。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check column_decoding
python -B component_runtime.py run column_decoding
```
