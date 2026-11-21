# pipeline_schedule

输入字段为 layers, world_size, microbatches。缺省字段沿用原题约定。

输出 partitions 和 AFAB 的 events；层边界为 floor(n*r/world)，保留正序前向、逆序反向及跨 stage 发送。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check pipeline_schedule
python -B component_runtime.py run pipeline_schedule
```
