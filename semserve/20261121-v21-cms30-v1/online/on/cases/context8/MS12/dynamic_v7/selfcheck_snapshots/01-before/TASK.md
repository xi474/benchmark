# 午餐供应波动下的全周菜单承诺

食堂要发布可随交货情况调整的菜单。员工调查、菜谱和供应情景均在输入中。一份政策须覆盖每个情景；每天开餐前只能使用到当天为止已观察到的交货信息。

`groups` 每行为 `[群体,人数,禁用配料列表,喜欢的品类列表]`。每道菜有 `id,cat,ingredients,difficulty,cost`。难度超过 4 的菜不能供应；任一群体禁用该菜中的任何配料，这道菜即不可用。某群体喜欢该菜的品类时，该群体每人获得一分满意度。cost 是该菜供应全体一天的整数成本。

`scenarios` 每条有正整数权重 `weight` 和等长的交货标签序列 `signals`。标签含义见 `delivery`，值是当天实际可用的配料列表。每条完整路径不同。第 d 天具有相同 d 个标签前缀的情景，必须供应同一道菜。每天一道，所有配料均要可用；每条实际路径上不得重复菜名、相邻两天不得同品类，全路径总成本不超过 `budget`。

一个情景的服务分是其各天满意度相加后在群体中取最小值，使用**每人**的满意度。情景的总人次分是各群体的每人满意度乘人数后相加。选择政策时依次最大化所有情景中的最低服务分、最大化按情景权重相加的总人次分、最小化按情景权重相加的全路径成本。权重直接相乘，不归一化。

按标签前缀的字典序排列所有不同的非空前缀，短前缀排在其扩展之前。输出这些前缀 `histories` 及 `optimal`。无可行政策时 optimal 为 null。否则含 `floor,utility,cost,count,menu,allowed`。count 数不同的前缀到菜名映射，menu 是所有最优政策中字典序最小的菜名向量，allowed 按同一前缀顺序逐一列出至少一个最优政策会选的菜名（各自升序）。不要求能将不同前缀的 allowed 任意组合为同一政策。最多 5 天、12 道菜和 12 个不同前缀。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/scenario_prefixes/work.py` | 输出 [信号历史,该完整叶的权重或 null]，去重生成所有非空前缀，按历史字典序排列。 | `components/scenario_prefixes/result.json` |
| `components/menu_eligibility/work.py` | 每个到货信号映射至可供菜品 ID，保持 recipes 顺序，检查难度、原料可得性和过敏限制。 | `components/menu_eligibility/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check scenario_prefixes
python -B component_runtime.py run scenario_prefixes
python -B component_runtime.py check menu_eligibility
python -B component_runtime.py run menu_eligibility
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
