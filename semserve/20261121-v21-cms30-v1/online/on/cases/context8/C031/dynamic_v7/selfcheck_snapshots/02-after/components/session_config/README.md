# session_config

输入字段为 startup, timeout_seconds, steps。缺省字段沿用原题约定。

输出 rc（固定主提示 PROMPT>、续行提示 CONT>、禁用历史、追加 startup）、timeout（缺省 4）、markers（原顺序的 until，可为 null）。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check session_config
python -B component_runtime.py run session_config
```
