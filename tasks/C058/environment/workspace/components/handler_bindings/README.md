# handler_bindings

输入字段为 handlers, program。缺省字段沿用原题约定。

输出 [处理器声明顺序映射,叶节点到通知清单的映射]。叶节点按同一树位置编码；通知名去重并按声明顺序排列，含 rescue、always。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check handler_bindings
python -B component_runtime.py run handler_bindings
```
