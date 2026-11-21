# buyer_totals

输入字段为 buyers, orders。缺省字段沿用原题约定。

按买家 ID 汇总属于 Cameras 或 Electronics 的行金额，每行只计一次；无购买为零。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check buyer_totals
python -B component_runtime.py run buyer_totals
```
