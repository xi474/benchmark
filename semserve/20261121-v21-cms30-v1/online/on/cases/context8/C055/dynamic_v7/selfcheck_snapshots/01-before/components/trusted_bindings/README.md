# trusted_bindings

输入字段为 sources。缺省字段沿用原题约定。

解析受信任文档的覆盖和文档内锚点。每个有效键输出 [原源序号,声明位置,[值位置,文本,是否密文,来源是否可信]]；位置为 [源名,行,列]。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check trusted_bindings
python -B component_runtime.py run trusted_bindings
```
