# line_windows

输入字段为 orders, released, routing, lines, wip, freeze, changeover。缺省字段沿用原题约定。

按工单 ID 输出合格产线及可行起止窗口三元组，按产线及起点的原遍历顺序。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check line_windows
python -B component_runtime.py run line_windows
```
