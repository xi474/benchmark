# io_buffers

输入字段为 files, stdin_hex。缺省字段沿用原题约定。

返回 [文件名字节数组映射,标准输入字节数组]，未指定文件或 stdin 时为空。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check io_buffers
python -B component_runtime.py run io_buffers
```
