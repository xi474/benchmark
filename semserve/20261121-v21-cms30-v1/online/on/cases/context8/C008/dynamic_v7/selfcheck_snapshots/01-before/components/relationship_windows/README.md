# relationship_windows

输入字段为 links, merges。缺省字段沿用原题约定。

将链接和合并登记为 [起点,终点,生效时刻,失效时刻]。保留原顺序并补齐缺省区间。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check relationship_windows
python -B component_runtime.py run relationship_windows
```
