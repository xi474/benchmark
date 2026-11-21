# service_quorums

输入字段为 services。缺省字段沿用原题约定。

按服务 ID 索引门槛及直接输入，值为 [need,inputs]；保留输入顺序和共享故障域。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check service_quorums
python -B component_runtime.py run service_quorums
```
