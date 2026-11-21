# directory_snapshots

输入字段为 nodes, mounts, scans。缺省字段沿用原题约定。

按扫描轮次生成映射，从每个完成目录的逻辑路径映射至 [保留文件映射,可见子目录名升序数组]。按轮累计替换节点。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check directory_snapshots
python -B component_runtime.py run directory_snapshots
```
