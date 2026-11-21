# observed_outages

输入字段为 queries, log。缺省字段沿用原题约定。

为每个查询逐时隙列出当时可见且实际为 down 的域名数组，升序；按有效时刻再按看到时刻选择最新记录。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check observed_outages
python -B component_runtime.py run observed_outages
```
