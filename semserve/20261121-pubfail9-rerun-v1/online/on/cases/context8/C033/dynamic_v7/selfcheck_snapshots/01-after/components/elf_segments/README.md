# elf_segments

输入字段为 elf_hex。缺省字段沿用原题约定。

输出 [入口地址, [[地址,字节],…]]，按加载后的地址升序排列，包括 PT_LOAD 零填充。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check elf_segments
python -B component_runtime.py run elf_segments
```
