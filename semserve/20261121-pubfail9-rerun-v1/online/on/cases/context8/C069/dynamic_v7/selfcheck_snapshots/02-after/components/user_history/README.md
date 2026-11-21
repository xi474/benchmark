# user_history

输入字段为 events, user。缺省字段沿用原题约定。

记录各续期事件发生时的用户快照，重放 update_user 的 roles、traits；以原位置字符串为键。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check user_history
python -B component_runtime.py run user_history
```
