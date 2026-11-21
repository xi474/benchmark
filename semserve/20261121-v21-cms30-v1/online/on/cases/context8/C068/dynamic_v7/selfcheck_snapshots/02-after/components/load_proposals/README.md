# load_proposals

输入字段为 events。缺省字段沿用原题约定。

为每个 get 的原始位置生成 [若启动时的完成时刻,value,error]；只有命中未复用时才实际启动。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check load_proposals
python -B component_runtime.py run load_proposals
```
