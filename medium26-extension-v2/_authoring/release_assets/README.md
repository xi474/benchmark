# 改编26题 v2：20题原版 + 6题规格修订

本版为26题、93个核心组件、四类结构的独立2.0.0发布，针对MP04、MP08、MP09、MP10、MP11、MP24修复公开规格缺口。任务ID和目录结构沿用v1；既有业务算法、输入、契约和评分语义保持，六题的题面与接口说明对齐本地受限范围。

## 版本与难度

v1保留，不被覆盖；原56题五次基线属于旧实验条件。本发布不附带完整新版模型校准结果；六题新版复测独立记录，不能把旧版六题成绩直接作为新版成绩。manifest中的M只保留历史中等设计目标，不是v2实测档；本次参考解与负例验收也不是模型能力评估。

## 20 + 6 的组成

20题的TASK与初始workspace和v1逐字节相同；MP04、MP08、MP09、MP10、MP11、MP24使用单独发布的六题修订版，TASK与初始workspace逐字节一致。全部26题集中放在本目录tasks下，共93个核心组件。六题单独包是此26题的子集。

详见[逐题组成与字节比对](review/distribution_composition.json)。原14题、Mixed16和本26题共56道不同题目；同事新增Long Parallel10另行统计。

## 阅读入口

- [六题修订、上游与本地归因](docs/修订与来源归因_v2.md)
- [26题目录与DAG](docs/26题中文目录与DAG.md)
- [原始来源及难度信息](docs/原题来源与难度标注.md)
- [参考解和负例验收](review/validation_report.json)
- [v1/v2语义与文件兼容性](review/version_compatibility.json)
- [六题针对性规格验收](review/spec_v2_regression.json)
- [部分奖励评分验收](review/partial_reward_validation.json)
- [26题Agent任务包](../medium26-extension-v2-agent.zip)
- [六题独立修订集](../medium6-specfix-v2/README.md)

## Agent输入与验收

只向Agent提供单题TASK.md和初始workspace；作者材料、来源审计、DAG、参考解和verifier留在工作区外。任务只需Python>=3.11标准库和本地小型合成输入，无真实账号、常驻服务、GPU或实时等待。

公开冒烟：在候选workspace运行python3 check.py。正式验收：

```bash
python3 verifier/verify.py --entry context8/dinner_contact_checkout --workspace /path/to/candidate
```

部分奖励沿用原有policy与打分代码，配套catalog只指向本版26题并更新保护哈希：

```bash
python3 verifier/partial_reward/score.py --benchmark-root . --task medium/MP10 --workspace /path/to/candidate
```

## 作者复验与重建

```bash
python3 _authoring/build.py --dest /tmp/new-medium26-v2
python3 _authoring/qa.py --root . --work /tmp/medium26-v2-qa
python3 _authoring/spec_v2_regression.py --root . --work /tmp/medium26-v2-qa
python3 _authoring/package.py --root .
```

构建配图需要Pillow及中文字体；任务和verifier只用标准库。QA工作目录必须在发布包外。SHA256SUMS覆盖发布文件，不含自身、压缩包或Python缓存。Agent zip仅含tasks目录。
