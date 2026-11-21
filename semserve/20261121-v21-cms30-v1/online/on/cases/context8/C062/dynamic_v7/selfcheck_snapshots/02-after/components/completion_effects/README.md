# completion_effects

输入字段为 events。缺省字段沿用原题约定。

对每个 complete 事件按原始位置记录 [正常完成事件名,新 revision 或 null]。取消与关闭优先级由整合逻辑决定。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check completion_effects
python -B component_runtime.py run completion_effects
```
