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

`/logs/verifier/score.json` 记录正式严格通过、核心转换用例通过率、各项检查、完整性和六位小数 reward。`reward.txt` 为该题加权得分，59 题单轮总满分 **138**。严格通过率以题为单位，核心转换用例可另报总通过数除以总用例数。缺整份评分的题在汇总中报告覆盖数。

原始 295 份定档成绩保存在 `evidence/<ID>/r01.json` 至 `r05.json`，每题的 `replay.json` 对照原判分器和 v2.0.0。170 份历史回执可以按新标准复算，其余注明缺少的证据。MS42 在冻结条件下为 0/5，等价的整数成绩表示对照为 4/5。[MS42 对照记录](evidence/MS42/replay/grade-units-control.json)

正式计分沿用各题在模型运行前冻结的权重，39 题满分 2，20 题满分 3。例如 MP17 的五轮实测档为难，冻结满分为 2；MS02 的五轮实测档为中，冻结满分为 3。参考解与初始工作区的逐题验收见[离线验收记录](validation/offline.json)。

