# 金融素养工作坊的双向稳定分班

两门财务课共用一批由近期市场事件组成的工作坊；需要知道严格按照学生选择和班方优先级，可安排多少人，以及哪些席位始终相同。

grades 行 [学生,课程,得分或 null,满分]。只取课程 16、17 的非空评分，先算每次得分/满分，再对该生等权平均；比例低于 0.60 为 N，低于 0.75 为 D，其余为 P。至少有一次有效评分者进入分班。market 行 [事件ID,教学日,开盘价,收盘价]。以全体行情的最后教学日 L 为锚点，仅保留 L−29 到 L（含）的事件，按 abs(收盘−开盘)/开盘 降序、事件 ID 升序选前 top 个。每个事件对应一场工作坊。rooms 对每个事件给出 `capacity` 和 `tiers`（形如 [["N"],["P","D"]]，从优先到次要，同组并列，未列层级不可录取）。

prefs 为学生 ID 到偏好组的映射，组间从高到低，组内并列，未列的事件不可接受。每个情景 cancel 关闭已入选事件中的若干场，关闭后不从榜单补位。每人最多一席，各场不得超容量。双方均可接受才可配对。未分配比任何可接受场次都差。

一个分班是**弱稳定**的，当且仅当不存在这样的未配对学生 s 与开放场次 w：s 严格偏好 w 胜过现状，且该场有空席或严格偏好 s 胜过某位已入班者。零容量的场不能形成阻挡。只计学生到场次的映射，不区分同场座位。

返回按 cancel 顺序的列表。每项含 `sizes`（各稳定映射的 [分到人数,映射数]，按人数升序）、`forced`（所有达到最大分到人数的稳定映射都包含的 [学生,场次]，升序，不列未分配者）、`example`（这些最大映射中，按学生 ID 升序列出所分场次的字典序最小向量；未分配写空串）。每个双向可接受图的独立部分至多 8 名学生，各人至多 5 个开放可选项。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/student_tiers/work.py` | 使用 16、17 号课程非空成绩的精确分数比，按原门槛输出学生到 P/D/N 层级映射。 | `components/student_tiers/result.json` |
| `components/market_ranking/work.py` | 按最新市场日的 30 天窗口、相对绝对涨跌幅和代号打破平局，返回前 top 个房间代号（保持排名）。 | `components/market_ranking/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check student_tiers
python -B component_runtime.py run student_tiers
python -B component_runtime.py check market_ranking
python -B component_runtime.py run market_ranking
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
