# Capstone Upstream59 v2.1.0 · 预建文件版

这是从 [Upstream59 v2.0.0](https://github.com/xi474/benchmark/tree/d15d560fbcfeb5fa061b6549a46a220184021e76) 派生的工作区版本。20 道 C 题和 10 道 MS 题使用独立业务文件及预建中间产物。25 道 MP 和 4 道 N 题沿用上一版。

[改编与验收](WORKFILES.md) · [逐题来源和原版五测](TASKS.md) · [评分规则](scoring/README.md) · [离线验收](validation/offline.json)

## 下载 v2.1.0

| 使用场景 | 下载内容 |
|---|---|
| 自研 harness 运行 C/MS 30 题 | [30 题接入包](https://github.com/xi474/benchmark/blob/release/downloads/capstone-c-ms30-workspaces-v2.1.0.zip?raw=true)，含任务说明、工作区和每题的 `work_units.json` |
| 正式评测全部 59 题 | [完整评分包](https://github.com/xi474/benchmark/blob/release/downloads/capstone-upstream59-workfiles-v2.1.0.zip?raw=true)，含题包、独立 verifier、参考解、评分规则与验收回执 |

两个 ZIP 的 SHA-256 见[下载校验清单](downloads/SHA256SUMS)。测试 C/MS 时，向 agent 提供接入包中的对应题目，评测端使用同版本完整包。

## 运行


使用 Linux Docker 和支持独立 verifier 环境的 Harbor（历史实验使用 0.24.0）。从仓库根目录或完整 ZIP 解压目录执行以下命令。第一条构建共享基础镜像，第二条用参考解检查单题环境。

```sh
docker build -t capstone-upstream59:2.0 -f runtime/Dockerfile .
harbor run --path tasks/MP01 --agent oracle
python3 validate_release.py
```

同一题使用同一个 `tasks/<ID>` 入口切换被测 harness。仅向 agent 提供 `instruction.md` 和 `environment/` 中的工作区。隐藏检查、参考解及历史成绩位于评测端。校准环境和新的可构建镜像应分别登记；横向实验应固定实际使用的镜像摘要、harness、模型、模式、预算和重试规则。

## 结果

[Qwen3.8-Max 关闭推理：六套 Harness × 59 题完整报告与全部 trace](results/upstream59-v21-qwen38-max-off-20261126/README.md)。覆盖354个选定题位及全部394条attempt记录（387次实际模型运行、7条零发送隔离）；含ACC、API、新版reward、完整E2E、tokens、缓存、目录价和全部旧异常。每题trace独立下载，附原文件与发布副本SHA-256。

11 月 25 日更新 · [SP 严格通过率改进实施手册](results/upstream59-sp-failure-analysis-20261124/updates-20261125/SP严格通过率改进实施手册-20261125.md) · [Nanobot 工具链分析与 SP 改进建议](results/upstream59-sp-failure-analysis-20261124/updates-20261125/Nanobot工具链分析与SP改进建议.md) · [配套证据与离线复核](results/upstream59-sp-failure-analysis-20261124/updates-20261125/README.md)

[SP、Codex 与 DSH 的严格通过率分析和 SP 改进方案](results/upstream59-sp-failure-analysis-20261124/README.md)。收录 SP 的 59 题索引、134 个未通过的核心 API 检查、Codex 与 DSH 的主动补测轨迹、16 页汇报 PPT、证据数据及离线复核工具。历史实测成绩与改进方案的预期收益分别列出。

[下载 DSH、Codex、Nanobot 各 59 题的原生 trace](results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/README.md)。共 177 份逐题归档，可查原生事件、工具记录、监控与网关账本，附 SHA-256 校验清单。

[SemServe 与六套 Harness 的 Upstream59 对照报告](results/upstream59-v21-semserve-vs-six-harnesses-20261123/README.md)。包含 59 题逐题数据、首轮与重放图表、执行耗时与 E2E 口径、模型成本和 trace 分析。

[下载 DeepSeek V4 Pro 普通模式完整评测矩阵（Word）](results/upstream59-v21-deepseek-v4pro-20261121/upstream59-v2.1.0-deepseek-v4-pro-matrix.docx?raw=true)。报告覆盖 59 题 × 6 套 Harness 的 354 格，包含 reward、严格通过、核心 API 检查、逐题 E2E、模型成本估算、委派调用、实际创建子 Agent 和工具执行区间重叠，以及汇总对比图。

`/logs/verifier/score.json` 记录正式严格通过、核心转换用例通过率、各项检查、完整性和六位小数 reward。`reward.txt` 为该题加权得分，59 题单轮总满分 **138**。严格通过率以题为单位，核心转换用例可另报总通过数除以总用例数。缺整份评分的题在汇总中报告覆盖数。

原始 295 份定档成绩保存在 `evidence/<ID>/r01.json` 至 `r05.json`，每题的 `replay.json` 对照原判分器和 v2.0.0。170 份历史回执可以按新标准复算，其余注明缺少的证据。MS42 在冻结条件下为 0/5，等价的整数成绩表示对照为 4/5。[MS42 对照记录](evidence/MS42/replay/grade-units-control.json)

正式计分沿用各题在模型运行前冻结的权重，39 题满分 2，20 题满分 3。例如 MP17 的五轮实测档为难，冻结满分为 2；MS02 的五轮实测档为中，冻结满分为 3。参考解与初始工作区的逐题验收见[离线验收记录](validation/offline.json)。

