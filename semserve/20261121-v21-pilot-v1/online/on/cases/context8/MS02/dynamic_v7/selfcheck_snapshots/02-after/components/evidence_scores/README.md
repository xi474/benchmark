# evidence_scores

输入字段为 topics, papers。缺省字段沿用原题约定。

按主题输入顺序生成评分表；每行把具有效章节证据的论文 ID 映射到该主题最高质量分。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check evidence_scores
python -B component_runtime.py run evidence_scores
```
