# response_deadlines

输入字段为 events。缺省字段沿用原题约定。

按 response 位置记录 [原因,到期时间]；失败优先于陈旧，延迟分别为 2000/1000，正常相应用 null。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check response_deadlines
python -B component_runtime.py run response_deadlines
```
