# store_initializers

输入字段为 events。缺省字段沿用原题约定。

对每个 open 事件按其原始位置（十进制字符串）建立初始状态，字段同最终 stores 项。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check store_initializers
python -B component_runtime.py run store_initializers
```
