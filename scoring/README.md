# 严格通过和 reward

采用项目冻结的 `delivery-bonus-50-v1`。每道题的登记表位于 `tasks/<ID>/tests/release-registry.json`。A 每个直接调用 transform 的核心用例占一项。B 每个组件的接口检查合为一项，两次独立合法输入均须通过。D 分别检查产物、模块和集成输出。P 执行整题公开检查一次。可选稳健性单列。具体 ID、组合关系和分母以登记表为准。

令 I 表示受保护文件和工作区通过完整性检查，K 为通过的登记项数，N 为冻结的 A+B+D+P 总数。公开通过要求 I 与 P 均成立。严格通过 S 要求 I 成立且 K=N。核心转换用例通过率只统计 A，独立加载、构建、公开执行和产物检查分别在 B、P、D 中体现。

```text
reward = I × W × (0.5 × K/N + 0.5 × S)
```

W 来自该题原先冻结的评分权重（E=1、M=2、H=3）。目录同时记录该权重和五轮定档。完整性失败得零分。已有完整回执时，缺失或超时的单项计失败；缺少整份回执或整项迁移依据时，结果记为未知。以十进制 ROUND_HALF_UP 对每题最终得分保留六位小数，然后逐题相加。例：W=2、K=30、N=31、完整性通过但未严格通过，得 0.967742。取得完整交付奖励时该题得 2.000000。

## 复算

```sh
python3 scoring/score_attempt.py --registry tasks/MS02/tests/release-registry.json --receipt evidence/MS02/r01.json
python3 scoring/score_run.py /path/to/one-harbor-job --out summary.json
python3 -m unittest discover -s scoring
```

新运行保留评测端的 `raw-checks.json`，可将其传给相同 CLI。MP 系列的新评分器分别执行直接转换以及两次干净目录下的独立构建，兼容旧题面要求的 parser 接口。在 MP 的历史评分中，单次接口检查以及部分转换与 parser 的合并检查缺少新协议要求的独立证据。原始 reward、版本和难度继续保存在历史记录中。外部上游原题的官方成绩和代理换算需要另行运行及取证，本发布包的分数仅适用于改编版。

整组汇总使用同一 harness、模型、模式、预算及重复轮次的作业目录。程序逐题读取原始回执，通过同一评分函数重算，遇到同题的多个回执会要求选择单轮。完整时输出 59 题严格通过率和总 reward；部分完成时列出未知题号、已评分子集的严格通过率、reward 小计和对应满分。核心转换用例的跨题微平均按已评分题目 A 类通过数之和除以 A 类总数之和计算。
