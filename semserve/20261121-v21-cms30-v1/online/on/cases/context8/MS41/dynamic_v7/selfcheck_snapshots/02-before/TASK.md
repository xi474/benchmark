# 推理方法综述中的自一致投票复核

综述团队需要在可核查的合成试验上比较文献中的逐次作答与自一致投票。每种方法有自己的转移表，可能反复修订，甚至永远没有答案。多次取样共享同一题目的潜在版本。请准确计算结果分布和正确作答的耗费。

`answers` 是互异的候选答案列表，越靠前平票时越优先；`correct` 指定正确答案。`profiles` 将题目版本 ID 映至正整数权重。一场投票开始时按权重随机选定一个版本，直到整场结束都固定不变。`methods` 每项含 id、votes（最多允许的票数）、start、graphs。graphs 为每个版本给出一张状态转移表。表的键是非终态名（和答案名不重复），值为 [目标,正整数权重,本次花费] 列表。每次按当前状态的出边权重比例随机选边并支付其非负整数花费。目标为答案名即交出一票，否则继续。闭合循环可以使这一票永不结束。各次从 start 重新开始，给定同一版本时各票独立。

每场至少发起一票。每次收到一票，按已收各答案票数决定当前领先者；票数相同取 answers 顺序在前者。如果即使余下每一票都投给任一同一个竞争者，当前领先者也仍能获胜，就立即宣布结果，否则发起下一票。已用完票数时也立即宣布。若某次发起的票永不结束，整场结果为未决，后续票不发起。

每种方法输出 id、prob（按 answers 顺序的最终胜出概率）、unresolved（未决概率）、launches（整场发起票数期望，含已经发起的未决票）、cost_if_correct（最终宣布正确时，所有已发起票花费之和的条件期望；正确概率为零则为 null）。所有概率和期望都用最简 [分子,正分母]。按正确概率降序、方法 ID 升序输出数组。最多 4 个答案、7 票、每个版本 14 个非终态。不需要生成任何自然语言推理内容。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/ballot_rules/work.py` | 输出 [先验映射,方法提前决胜表]。先验为最简分数。每种方法列出从零票起可达的计数状态（键为逗号分隔的答案票数）；值是已经胜出的答案下标或 null。决胜后不扩展。 | `components/ballot_rules/result.json` |
| `components/answer_absorption/work.py` | 按 method ID、profile 名输出 [各答案吸收概率,各答案加权成本质量]；向量元素均为约分的 [分子,分母]，保留 answers 顺序。 | `components/answer_absorption/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check ballot_rules
python -B component_runtime.py run ballot_rules
python -B component_runtime.py check answer_absorption
python -B component_runtime.py run answer_absorption
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
