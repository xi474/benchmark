# dish_requirements

输入字段为 dishes, max_difficulty。缺省字段沿用原题约定。

返回合格的三类菜品组合及合并需求，格式 [菜品 ID 数组,原料到数量映射]，按菜品字典序枚举。

在工作区根目录运行以下命令。

```sh
python -B component_runtime.py check dish_requirements
python -B component_runtime.py run dish_requirements
```
