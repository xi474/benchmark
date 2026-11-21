# record_subjects

输入字段为 records。缺省字段沿用原题约定。

按记录顺序产生 [表名,行号,时间,[租户,主体]]，为跨表归一化保留租户作用域。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check record_subjects
python -B component_runtime.py run record_subjects
```
