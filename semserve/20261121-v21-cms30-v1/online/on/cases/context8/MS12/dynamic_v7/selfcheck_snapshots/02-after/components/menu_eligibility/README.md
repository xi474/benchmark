# menu_eligibility

输入字段为 recipes, groups, delivery。缺省字段沿用原题约定。

每个到货信号映射至可供菜品 ID，保持 recipes 顺序，检查难度、原料可得性和过敏限制。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check menu_eligibility
python -B component_runtime.py run menu_eligibility
```
