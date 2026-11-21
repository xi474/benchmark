# 三道工作坊菜品的合并采购与可执行备料

活动组从三个不同品类选三道容易制作的菜。输出每个可能菜品组合的最低成本材料单及可以实际执行的共用备料顺序。

dishes 行 [菜ID,品类,难度,完整用料对象]，仅候选难度 ≤ max_difficulty 的菜。三道菜必须不同品类。三份用料的同名原料数量相加；准备结束时必须**同时**满足整单，允许留余。stock 是起始库存。offers 行 [商品ID,一包所含物料对象,一包价格,最多购买包数]。可在开工前购买整数包，同一包的所有物料同时到账。prep 行 [工序ID,一次所耗物料对象,一次产出物料对象,最多执行次数]。仅在全部耗材当前到位时才能执行，先扣耗材、再加全部产出；副产物可供后续使用。不同工序之间可能构成循环，不能预支尚未产出的原料。所有数量、价格均为非负整数，并且每个报价的价格为正。

输出按升序菜 ID 组成的三元列表的字典序，每个元素含 `dishes` 和 `plan`。无可行采购/备料方案，plan 为 null。否则依次最小化总价、采购包数、按报价 ID 升序的采购数量向量、工序总次数、工序 ID 序列字典序。plan 含 `cost,buy,steps,left`。buy 为按报价 ID 升序的完整数量向量（含零），steps 为实际执行顺序，left 为交付三道菜用料之后剩余的**正数**物料对象。上限为 10 道菜、6 个报价、总计最多 16 次实际备料。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/dish_requirements/work.py` | 返回合格的三类菜品组合及合并需求，格式 [菜品 ID 数组,原料到数量映射]，按菜品字典序枚举。 | `components/dish_requirements/result.json` |
| `components/purchase_baskets/work.py` | 输出所有限量采购篮 [总价,总件数,按排序后 offer 的购买数量向量]；按这三项升序排列。 | `components/purchase_baskets/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check dish_requirements
python -B component_runtime.py run dish_requirements
python -B component_runtime.py check purchase_baskets
python -B component_runtime.py run purchase_baskets
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
