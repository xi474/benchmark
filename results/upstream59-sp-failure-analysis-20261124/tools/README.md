# 离线复核与逐题数据导出

在 `xi474/benchmark` 的完整 `release` 分支检出中，进入本报告目录后执行下列命令。使用 Python 3.9 或更高版本及标准库。报告、证据、`semserve/`、`scoring/` 和原生 trace ZIP 均已检出时，全程可离线执行。

```bash
python tools/verify_review.py
python tools/verify_review.py --output-dir review-export
```

默认命令只打印汇总。第二条同时在新建或空的目录中写出 `review.json`（首轮、实际重放、采纳成绩、逐项失败 ID、修复建议及 DSH 分类）和 `tasks.csv`（59 行逐题对照）。脚本从自身位置向上定位仓库；在独立拷贝下运行可显式传入 `--release-root <仓库根>` 和 `--evidence-dir <本包的evidence目录>`。未下载 ZIP 时，`--skip-native` 可仅复核评分与标注汇总，输出的 `native_sha256_and_lines_checked` 将为 false。完整档案复核应使用默认模式。PPT 为阅读材料，程序无须读取它。

| 核验对象 | 实际操作 | 本版对照值 |
|---|---|---|
| SP 首轮及重放 | 由已发布的 task-metrics 定位归档 score.json，重数 A/B/D/P，核对完整性并调用 release 自带的 workspace_reward.py；重放仅在登记的公开通过条件满足后采用 | 59 份首轮与 9 份实际重放回执，采用 6 个重放。首轮严格 25/59、API 633/803、reward 78.469237。采用后严格 28/59、API 669/803、reward 85.361619 |
| 失分及修复 | 用选定身份列出各失败 ID，并与发布矩阵逐一比对。核对逐题诊断的题号集合 | 当前未严格通过 31 题，A 失败 134 个；加上 C069、MP14、MP25 三道重放后恢复题，共 34 道诊断 |
| DSH 自测 | 校验 59 个原生 ZIP 的 SHA-256、试次身份、所引公开检查工具回执和后续测试所在行；合并每题已审阅的业务场景条目 | 53 题在运行中观察到公开绿，45 题实测自造业务输入，场景下界 299 个。四组严格通过分别为业务新例 33/45、仅通用输入 1/3、仅公开复核 2/5、未定位公开绿 0/6。MS02、MP15 能串联原例发现、修实现、同输入通过 |

场景和因果链以人工逐条审阅标注为依据。脚本能检查档案身份、行号、时序和合计，单靠 tool_call 条数无法重新判断两个业务输入是否算同一场景。建议对有争议的题从随附 DSH 场景索引进入归档行号复核。

原料位于仓库的 `results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json`、`semserve/` 下的 68 个评分回执，以及 `results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/` 下的 ZIP。包内使用 `evidence/{C,MP,MSN}.json`、`evidence/scenario-{C,MP,MSN}.json` 和 `evidence/dsh-postpublic/audit.json`。
