# retry_faults

输入字段为 corrupt_attempts, max_retries。缺省字段沿用原题约定。

按块标签返回可发生的损坏尝试号，限制在 0 至 max_retries，升序去重。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check retry_faults
python -B component_runtime.py run retry_faults
```
