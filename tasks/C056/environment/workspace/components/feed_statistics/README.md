# feed_statistics

输入字段为 feeds。缺省字段沿用原题约定。

每个 host/stream 返回各次循环读取的 [items,数量,总和] 列表，保持原顺序。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check feed_statistics
python -B component_runtime.py run feed_statistics
```
