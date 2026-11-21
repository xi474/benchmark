# Capstone Upstream59 v2.0.0

59 道公开上游改编题，用于比较 agent harness 完成多阶段任务的能力。每题提供 Harbor 工作区、公开检查、独立评测入口、参考解和逐题来源。历史校准使用 Terminus 2 与 DeepSeek V4 Pro 普通模式，每题五轮。按原验收口径，中档 20 题，难档 39 题。

[下载完整题库](https://github.com/xi474/benchmark/raw/refs/heads/release/downloads/capstone-upstream59-v2.0.0-source-r1.zip) · [下载校验值](https://github.com/xi474/benchmark/blob/release/downloads/SHA256SUMS) · [逐题来源与分母](TASKS.md) · [评分协议](scoring/README.md) · [机器可读目录](catalog.json)

## 题号与来源

| 前缀 | 本地编题批次 | 本版题数 | 本版题目的公开上游 |
|---|---|---:|---|
| `C` | 100 道上游候选 | 20 | Terminal-Bench 4.1（5）、Terminal-Bench 2.0（4）、SWE-bench Pro（11） |
| `MP` | 中等难度与并行机会选题 | 25 | SWE-bench Verified（6）、SWE-bench Pro V2（7）、Terminal-Bench（4）、GAIA2 公开 mini / validation（8） |
| `MS` | MS-Eval 改编 | 10 | MS-Eval（10） |
| `N` | 新增 30 道候选 | 4 | SWE-bench Verified（1）、SWE-bench Pro（1）、Terminal-Bench 2.0（2） |

例如，MP17 最初按中等难度与并行机会选入，最终五测定为难档。各题沿用原批次序号，方便对照历史成绩。[前缀命名与例子](provenance/README.md) · [59 题逐题来源](TASKS.md)

当前下载包带有 source-r1 来源注释。早期实验可按[原始 v2.0.0 压缩包](https://github.com/xi474/benchmark/raw/refs/heads/release/downloads/capstone-upstream59-v2.0.0.zip)的校验值复核。

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

发布镜像上全部 59 份参考解严格通过，合计 138/138；59 个初始工作区共得 0 分。通过 Harbor 0.24.0 启动的四次端到端验收涵盖 MP17、C008、MS11、N22，包含三份参考解和一次空代理运行。[Harbor 原生入口验收](validation/harbor-smoke.json)

[历史六个 harness 的同版覆盖](evidence/six-harness-history.json) · [上一版 97 题的固定快照](https://github.com/xi474/benchmark/tree/912329e6c4ac12b6677d25697db590c1fa7d2468/capstone-benchmark-v1.1.0)
