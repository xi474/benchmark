# block_manifest

输入字段为 file_hex, chunk_size, thumbnail_hex。缺省字段沿用原题约定。

返回 [kind,index,hex] 列表；若有缩略图则排首，再按块大小顺序切出文件块。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check block_manifest
python -B component_runtime.py run block_manifest
```
