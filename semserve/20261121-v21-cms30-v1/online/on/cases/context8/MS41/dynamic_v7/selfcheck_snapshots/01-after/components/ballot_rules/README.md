# ballot_rules

输入字段为 profiles, methods, answers。缺省字段沿用原题约定。

输出 [先验映射,方法提前决胜表]。先验为最简分数。每种方法列出从零票起可达的计数状态（键为逗号分隔的答案票数）；值是已经胜出的答案下标或 null。决胜后不扩展。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check ballot_rules
python -B component_runtime.py run ballot_rules
```
