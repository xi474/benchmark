# answer_absorption

输入字段为 methods, profiles, answers。缺省字段沿用原题约定。

按 method ID、profile 名输出 [各答案吸收概率,各答案加权成本质量]；向量元素均为约分的 [分子,分母]，保留 answers 顺序。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check answer_absorption
python -B component_runtime.py run answer_absorption
```
