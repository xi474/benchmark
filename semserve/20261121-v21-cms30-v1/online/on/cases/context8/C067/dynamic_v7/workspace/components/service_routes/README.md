# service_routes

输入字段为 clusters, events。缺省字段沿用原题约定。

按事件位置返回请求当时的 [集群模式,服务是否可用]；合并端负责授权优先和实际计数。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check service_routes
python -B component_runtime.py run service_routes
```
