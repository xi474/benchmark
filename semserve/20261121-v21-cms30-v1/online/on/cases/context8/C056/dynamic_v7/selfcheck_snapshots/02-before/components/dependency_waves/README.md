# dependency_waves

输入字段为 tasks。缺省字段沿用原题约定。

返回各依赖批次，每批含按 ID 升序排列的任务 ID。同批共享同一事实快照。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check dependency_waves
python -B component_runtime.py run dependency_waves
```
