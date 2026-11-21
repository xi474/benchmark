# deadline_windows

输入字段为 assignments, slots。缺省字段沿用原题约定。

为有截止日的作业返回 [需求,合格时段 ID 升序数组]，先按原始时段和七天半开窗口筛选。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check deadline_windows
python -B component_runtime.py run deadline_windows
```
