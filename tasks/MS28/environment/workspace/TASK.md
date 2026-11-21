# 截止日辅导窗口的共同容量瓶颈

原始作业、日历提醒与能提供辅导的时隙分开维护。教务处希望知道需要把辅导资源至少按多大比例扩容，以及哪些作业共同形成不可拆的瓶颈。

assignments 行 [作业ID,截止日或 null,所需辅导点数,可服务时隙ID列表]。只为有截止日的作业发提醒。slots 行 [时隙ID,所在教学日,可提供点数]。所有点数为正。对某作业，只有同时列在其可服务清单中、且处于截止日之前七天的时隙才有效，日期条件是 due−7 ≤ day < due。withdrawals 列出几种独立停开时隙的情景。时间使用教学日整数；辅导点数可以分拆流向多个有效时隙，每个时隙容量只使用一次。

对每个情景，若任何有截止日的作业没有有效时隙，返回 {"unserved":[全部这类作业ID升序]}。若没有任何有截止日的作业，则返回 {"empty":true}。其他情况，对任意非空作业集合 S 定义负载比为「集合所需点数总和 / 集合的有效时隙并集容量总和」。最大负载比即资源至少要达到原容量的倍数，可以小于一。达到此比率的集合称为紧集。

返回 `peak`（最简分数 [分子,正分母]）、`count`（不同非空紧集数量）、`minimal`（所有按包含关系极小的非空紧集）、`implies`（按作业 ID 升序的 [作业ID,升序作业列表]，仅对出现在至少一个紧集中的作业给一行；列表列出每个包含它的紧集也包含的其他作业，不含它自己）。minimal 每个成员列表升序，各列表先按长度再按字典序。输出按 withdrawals 顺序排列。有效作业和时隙的二分图每个无向连通块最多 14 道作业，整校至多 64 道。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/deadline_windows/work.py` | 为有截止日的作业返回 [需求,合格时段 ID 升序数组]，先按原始时段和七天半开窗口筛选。 | `components/deadline_windows/result.json` |
| `components/remaining_slots/work.py` | 每个撤回情景返回仍可用的时段映射，时段 ID 对应 [时刻,容量]。 | `components/remaining_slots/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check deadline_windows
python -B component_runtime.py run deadline_windows
python -B component_runtime.py check remaining_slots
python -B component_runtime.py run remaining_slots
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
