# 跨年课程的可比考核与成绩变化

教务处要对照两个秋季学期的同一课程。新版课程改了考核 ID 和方法标签，部分先修关系也有变化。请在统一的标签对照规则下找出可比较的考核，并报告这些证据在成绩变化上允许哪些结论。

`rubrics` 将每个旧方法标签映到允许对应的新标签列表。旧标签和所有列出的新标签数量相同。学校实际使用的字典必须是覆盖全部标签的允许双射，输入保证至少有一本。所有课程共享同一本字典。`courses` 以开课代码为键；只比较同时有 `前缀-2013J` 和 `前缀-2014J` 两期开课的前缀。每期开课含 items（每行 [考核ID,本期方法标签,提交分数数组]，null 表示未评分）和 edges（[先修ID,后修ID]，无环）。先后关系取完整图中的传递可达，即使中间考核未参与对齐。

每个对齐是若干 [课程前缀,旧考核ID,新考核ID]。仅允许同课程前缀且两边各有至少一个已评分提交的配对，两边的考核各最多使用一次。所有配对的标签对应必须能同时延伸为一本完整的允许双射。对同一课程中任两对，旧考核之间的先后关系必须与新考核之间完全一致，原本不可比较的两项仍须不可比较。不同标签字典只要得到相同的考核配对集合，就属于同一个对齐。

先最大化配对数 pairs，再最大化 support（每对取两边非空提交数的较小者，再求和）。返回 pairs、support、最优对齐数 ways、所有最优对齐共有的配对列表 forced（按三列字典序），以及 drift。对一个对齐，将所有参与的新版考核的所有非空提交合并求均值，减去旧版按相同方式合并所得均值；**不先取单项或单课程平均**。drift 给出在全部最优对齐中该差值的最小和最大，各为最简 [分子,正分母]。空对齐也算一种，若 pairs 为零则 drift 为 null。最多五个方法标签、三对课程、每期每门至多六项考核。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/rubric_mappings/work.py` | 返回 [所有可行映射位掩码,旧标签到各新标签的掩码映射]；位序按新标签升序的排列枚举。 | `components/rubric_mappings/result.json` |
| `components/course_evidence/work.py` | 为每门课生成 [项目统计,传递可达表]；统计行 [ID,标签,[成绩和分子,分母],非空数] 按 ID 排序，保留零成绩。可达表的值为有序 ID 数组。 | `components/course_evidence/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check rubric_mappings
python -B component_runtime.py run rubric_mappings
python -B component_runtime.py check course_evidence
python -B component_runtime.py run course_evidence
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
