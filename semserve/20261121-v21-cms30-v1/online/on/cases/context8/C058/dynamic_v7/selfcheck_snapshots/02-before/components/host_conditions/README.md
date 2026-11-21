# host_conditions

输入字段为 hosts, program。缺省字段沿用原题约定。

每个 host 对应一张节点表，按树位置（各级整数以 / 分隔）记录 [可执行,会失败]；包含块节点。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check host_conditions
python -B component_runtime.py run host_conditions
```
