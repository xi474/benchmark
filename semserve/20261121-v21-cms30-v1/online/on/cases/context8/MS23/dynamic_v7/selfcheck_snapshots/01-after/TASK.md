# 三个匿名反馈渠道的改进优先级

客户满意度调查、电商评论和售后回访分别以 0 到 k−1 记录从低到高的评级。三渠道覆盖同一批客户；为了保护匿名性，只留下三个两两交叉表。找出各报表共同允许的客户群像，判断推断出的改进方向是否依赖未知的逐人链接。

对每个输入快照，`ab[a][b]`、`bc[b][c]`、`ac[a][c]` 均为非负整数人数。`forbidden` 列出业务流程排除的 [a,b,c] 组合。一个解释是非负整数三维表 X[a,b,c]，三组二维投影必须逐格等于输入，禁用格为零。计数单位是不同的**人数表**；相同评级的客户不可区分。k 为 2、3 或 4。

一名客户获三项评级的中位数决定主判。中位数为 k−1 计 +1，为 0 计 −1，其他为 0。汇总成全体客户的净支持人数。输出与输入 snapshots 顺序一致。无相容表时为 null。否则返回 `tables`（相容表数）、`spectrum`（按净支持人数升序的 [净人数,表数]）、`guaranteed`（所有相容表中人数均大于零的格，按 a,b,c 排序，每项 [a,b,c,最小人数]）、`witness`（净人数最低的相容表中，按 a→b→c 的完整含零格人数向量字典序最小者，只输出非零格 [a,b,c,人数]，同序）。各道快照独立。总人数至多 40。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/margin_constraints/work.py` | 为每个快照输出 [ab 与 ac 各 a 总量是否相容,按 a,c 行优先展开的 ac 配额]。 | `components/margin_constraints/result.json` |
| `components/layer_candidates/work.py` | 为每个快照按 b 生成候选层数组。每层候选为 [按 a,c 行优先的计数向量,该层的中位数净分]，满足边际、禁止格和 ac 上限；按向量字典序。 | `components/layer_candidates/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check margin_constraints
python -B component_runtime.py run margin_constraints
python -B component_runtime.py check layer_candidates
python -B component_runtime.py run layer_candidates
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
