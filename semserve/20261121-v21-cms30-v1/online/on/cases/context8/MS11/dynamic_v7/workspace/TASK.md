# 匿名书店账户与学生成绩的关联区间

大学书店要判断电子产品消费与两门分析课的成绩是否同向。迁移时丢失了部分账户映射。实施 `transform(payload)`，用登记证据约束映射，再报告仍可能出现的所有关联结果。

- `students` 和 `buyers` 是两份等长的唯一 ID 名单。每名学生至少有一个课程 1 或 2 的已评分提交。`grades` 行是 [学生,课程,分数或 null]。只取这两门课程的非空分，求每人算术平均后乘 100，作为整数成绩 X。数据保证乘后为整数。
- `orders` 中每单有 `buyer,status,lines`，每个明细为 [类别列表,件数,单价分]。无论订单状态如何，只要类别包含 Electronics 或 Cameras，计入件数乘单价；同一个明细只计一次。每账户总消费分为 Y，名单中的每个账户都有此类购买。
- 登记证据 `evidence` 各行为 [来源,学生,账户,正整数强度]。一个来源对同一配对的多次观测只保留最大值。不同来源的值相加得到配对置信度。无证据的配对不可用。学生与账户要完整一一配对。
- 在可行映射中先最大化最低配对置信度，再最大化全部配对置信度之和。报告所有同时达到两项目标的不同映射数量。对每个最优映射计算整数关联分子 `n*sum(X*Y)-sum(X)*sum(Y)`，n 为全校本次名单长度。这个值与 Pearson 相关系数同号。报告最小和最大分子，以及分别达到两端时字典序最小的账户向量。向量按学生 ID 升序列账户 ID；报告还需要所有最优映射都采用的 [学生,账户]，按学生 ID 排序。
- 按 `drop` 中给出的顺序分别复算。其元素是 null（所有来源均在）或要完全撤回的单个来源名；每次均从完整数据独立撤回。输出列表，每项为 `{"drop":来源,"result":结果}`。无完整映射时结果为 null；有映射时结果含 `floor,total,count,min_num,max_num,min_buyers,max_buyers,forced`。同一数值的不同映射各自计数。

证据二分图的每个连通块每侧至多 14 个顶点；全校名单可跨多个块。公开文件给出完整输入和输出示例。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/student_scores/work.py` | 按学生 ID 输出课程 1、2 非空成绩的百分制整型均值（sum×100 整除数量）。 | `components/student_scores/result.json` |
| `components/buyer_totals/work.py` | 按买家 ID 汇总属于 Cameras 或 Electronics 的行金额，每行只计一次；无购买为零。 | `components/buyer_totals/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check student_scores
python -B component_runtime.py run student_scores
python -B component_runtime.py check buyer_totals
python -B component_runtime.py run buyer_totals
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
