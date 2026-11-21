# 题号怎么读，原题在哪里

题号由本地批次前缀和该批次的序号组成。发布时沿用原编号，便于把改编规格、上游原题和历次实验对应起来。筛选后出现跳号属于正常情况。

| 前缀 | 本地编题批次 | 本版题数 | 本版题目的公开上游 |
|---|---|---:|---|
| `C` | 100 道上游候选 | 20 | Terminal-Bench 4.1（5）、Terminal-Bench 2.0（4）、SWE-bench Pro（11） |
| `MP` | 中等难度与并行机会选题 | 25 | SWE-bench Verified（6）、SWE-bench Pro V2（7）、Terminal-Bench（4）、GAIA2 公开 mini / validation（8） |
| `MS` | MS-Eval 改编 | 10 | MS-Eval（10） |
| `N` | 新增 30 道候选 | 4 | SWE-bench Verified（1）、SWE-bench Pro（1）、Terminal-Bench 2.0（2） |

## 当时为什么这样编号

- **C**　按 100 道候选的清单顺序编为 C001–C100，可用 Candidate（候选）记忆。
- **MP**　早期选题目录使用 medium-parallel，Medium 对应设计时的中等目标，Parallel 对应筛选时看重的并行机会。原批次共 26 题。
- **MS**　沿用上游名称 MS-Eval 的 MS，为本项目改编题另编序号。原题可用 oracle166 中的任务名定位。
- **N**　当时以 new30 登记这批新增候选，N 可用 New（新增）记忆。本版采用该批次的盲编排版本。

C 的选题脚本按清单顺序生成三位序号。MP 最初复筛了 12 个候选，随后扩至 26 个。C 和 N 的英文助记依据候选表及批次目录；早期记录没有单独规定这两个字母的正式英文全称。

## 从编号查到原题

- **C007** 是 100 题候选表中的第 7 项，改编自 Terminal-Bench 4.1 的 `telecom-entity-resolution`。[来源记录](C007.json)
- **MP01** 来自 SWE-bench Verified 的 scikit-learn 投票器修复。**MP16** 则合并了 Sphinx 的三个上游实例。来源表按改编题计数，多源改编会列出所有原题。[MP01 来源](MP01.json) · [MP16 来源](MP16.json)
- **MS02** 是本地的第 2 个 MS-Eval 改编任务，其上游文件名为 `academic-literature-review.task.md`。本版的 MS02 来自首批十题，其余九题来自后续可委派任务筛选。[MS02 来源](ms-eval/MS02.json) · [MS-Eval 原仓库说明](https://github.com/LINs-lab/MS-Eval/blob/4c1bbd3dc0d736623bba563e56cfd8666f85daac/README.md)
- **N11** 属于新增 30 题批次，改编自 SWE-bench Verified 的 `sympy__sympy-17630`。[来源记录](N11.json)

查本项目实测难度，请看逐题表的「五测档」。例如 MP17 当初按中等目标入选，五次实测严格通过 0 次，最终定为难档。上游的原始标签另存于逐题来源记录。

[查看 59 题的原题标识、链接及实测档位](../TASKS.md) · [机器可读目录](../catalog.json)
