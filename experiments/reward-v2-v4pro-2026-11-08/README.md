# V4 Pro普通模式 reward-v2 运行结果汇报

2026-11-08发布至xi474/benchmark。任务集合为原14题、mixed16-v4的16题、Medium26的26题。数据集基线分支为`data/mixed16-v4-execution-2026-10-30`，提交`76275fc1bb87be85a0fa72c7202f09633ad223c7`。模型为DeepSeek V4 Pro普通模式；Chat Completions为thinking.type=disabled，Responses为reasoning.effort=none。

## 已完成范围

- 原七臂：Nanobot、OpenCode、Codex、DSH、LangGraph、LATTE planning-adapted、ROMA-local-C0，7×56=392个选定基线题位；LATTE四个独立补跑另列，原基线不覆盖。
- 新增独立AOrchestra比较臂：56个选定公开题位，全部有有效评分。它采用本地适配、串行委派及4096输出/160请求条件，不能称论文原条件或与其他Harness等限额排名。
- 合计448个基线/比较臂题位，加4个单列补跑。448不是满分数、不是全部正常终态；七臂仍包含无效提交、发送前预算跳过和证据失败。SDK历史不进入本次矩阵，纯native LATTE和LATTE-frozen也不混入。

## Medium26（26题）

| Harness | 题位 | API有效题数 | API微平均 | API宏平均 | 平均E2E秒 |
|---|---:|---:|---:|---:|---:|
| aorchestra | 26 | 26 | 15.17% | 14.76% | 279.90 |
| codex | 26 | 26 | 88.32% | 87.53% | 1504.06 |
| dsh | 26 | 26 | 81.49% | 81.71% | 640.04 |
| langgraph | 26 | 26 | 44.01% | 43.12% | 602.44 |
| latte-planning-adapted | 26 | 22 | 18.07% | 20.77% | 379.93 |
| nanobot | 26 | 26 | 76.78% | 77.06% | 927.59 |
| opencode | 26 | 26 | 29.14% | 31.49% | 282.06 |
| roma | 26 | 25 | 9.53% | 10.45% | 375.20 |

API微平均为api/通过检查总数除以有效检查总数，宏平均为有效题目准确率平均；无效提交/跳过/证据失败不伪装成可比较API 0%。原14题无api/分母，另列focused/检查。reward-v2按固定检查数量与难度上限计分，不能把reward归一化称为满分率。

## 文件索引

- [八臂×三数据集汇总CSV](harness-dataset-summary-24.csv) / [JSON](harness-dataset-summary-24.json)：reward、API、E2E、输入/输出/cache tokens、未知请求与估算费用。
- [Medium26逐题×八臂API准确率](api-task-matrix-medium26-eight-arms.csv)。
- [mixed16-v4逐题×八臂API准确率](api-task-matrix-mixed16-v4-eight-arms.csv)。
- [七臂原发布报告](seven-harnesses/README.md)、[392题全指标](seven-harnesses/cells-392.csv)、[原始结构化导出](seven-harnesses/results.json)、[四个独立补跑](seven-harnesses/latte-independent-repeats-4.csv)。原七臂包从研究仓库提交`d724c143cc931f0bb2d469fb54123ee4967abb70`逐字复制，原审计校验继续可用。
- [AOrchestra运行报告](aorchestra/REPORT.md)、[56题全指标JSON](aorchestra/results-56.json)、[逐题CSV](aorchestra/cells-56.csv)、[Medium26 CSV](aorchestra/medium26-cells.csv)、[来源验收](aorchestra/source-validation.json)。本地归档提交`114808e8c658faa5b697efd89360e77ce5a306af`，源文件SHA见审计。只转换本机路径为可移植定位符，不改数值或缺测状态。
- [七臂运行中multi-agent证据审计](seven-harnesses/MULTIAGENT.md)、[并行触发原因分析](parallel-analysis/REPORT.md)、[392题触发证据CSV](parallel-analysis/parallel-trigger-cells-392.csv)。原因分析仍只针对原七臂，不将AOrchestra计入其中。
- [自检关联窗口](seven-harnesses/self-check-loops.csv)：不代表完整模型分析/修复耗时或纯自检增量成本。
- [发布校验脚本](scripts/validate_publication.py)、[发布文件与来源SHA256](publication-audit.json)。

## 并行、时间与费用边界

跨题5/8并发与ROMA单Harbor/HTTP4不同，AOrchestra批次最多4/共享5；E2E含环境/Agent/verifier，属于各自资源条件下观测，不能直接推导Harness本身加速。

原七臂Codex1/56题创建3子线程；Nanobot/OpenCode/DSH的实际委派入口各56/56曾开放，但未调用；LangGraph27/56有worker生命周期重叠；LATTE adapted36/56有队友模型回合重叠、12/56执行期接受28个模型新任务，脚本/测试跨队友工具重叠未观察到；ROMA52/56叶活动重叠、39/56工具span重叠。AOrchestra47/56题触发子Agent、80份摘要回传、题内并行0。观测层不同，不能把调度/生命周期/模型回合/HTTP/工具并行合成一个指标，也不把固定Agent定义计作运行时新定义。

token来自去重实际结算，cache是输入的子集。部分未知用量保留null及已知下界，不以0填补；AOrchestra两题native summary总量缺失与provider-egress已结算口径分别保留。费用是估算，非账单；历史排除attempt的HTTP400/402/中断未知用量仍保留，不声称跨历史总账完整。

资源粒度为task-container；远程推理引擎GPU/显存/KV/queue/batch/能耗与per-agent cgroup等未观测项保持null。子任务完成/摘要回传不代表任务检查通过。

## 发布范围与复核

只发布结构化指标、公开任务标识、来源hash及分析报告；不上传原始提示、工具输出、凭据、私有任务或LATTE/ROMA上游源码。证据locator指向持有原始文件时可复核的位置，不表示GitHub包含原始日志。任务、verifier、policy与catalog字节不改。不要将本目录或作者验证材料挂载给被测Agent。

在本目录执行`python scripts/validate_publication.py`，可离线核验文件指纹、题位唯一性、API聚合、AOrchestra数值不变以及脱敏边界，无需API key或模型调用。
