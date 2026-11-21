# grant_catalog

输入字段为 access_requests。缺省字段沿用原题约定。

生成授权条目的有效条件和有序角色/资源集合。以原授权 ID 为键，每项含 approved、expiry、roles、resources。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check grant_catalog
python -B component_runtime.py run grant_catalog
```
