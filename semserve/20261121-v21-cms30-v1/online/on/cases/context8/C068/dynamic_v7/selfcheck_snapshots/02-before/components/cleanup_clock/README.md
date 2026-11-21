# cleanup_clock

输入字段为 ttl, events。缺省字段沿用原题约定。

按 get 驱动的 16×TTL 规则生成触发清理的 get 位置，以及下一次清理的时间。输出以位置字符串为键的映射。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check cleanup_clock
python -B component_runtime.py run cleanup_clock
```
