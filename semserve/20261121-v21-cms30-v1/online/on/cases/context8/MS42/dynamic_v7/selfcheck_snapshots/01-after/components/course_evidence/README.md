# course_evidence

输入字段为 courses。缺省字段沿用原题约定。

为每门课生成 [项目统计,传递可达表]；统计行 [ID,标签,[成绩和分子,分母],非空数] 按 ID 排序，保留零成绩。可达表的值为有序 ID 数组。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check course_evidence
python -B component_runtime.py run course_evidence
```
