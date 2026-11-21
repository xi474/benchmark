# batch_gradients

输入字段为 layers, world_size, microbatches。缺省字段沿用原题约定。

按实际 stage 保留每个微批激活并反传；返回整题格式的 loss 和各层 gradients，采用微批等权和 float64。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check batch_gradients
python -B component_runtime.py run batch_gradients
```
