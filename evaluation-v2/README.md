# 评审与 reward 标准 v2

本版本只调整工作区外的评审汇总、诊断与 reward。原始14道简单任务、Medium26和Mixed16 v4的任务说明、初始workspace、输入、契约、公开检查、参考算法与既有测试语义均保持原有版本；旧0/1结果保留。

## 1. 难度满分与公式

当前项目采用设计难度：E简单、M中等、H困难。默认满分分别为 **1、2、3**，存于可信的`policy.json`，不是实验测出的客观难度分数。调整这些满分时必须发布新政策版本。

**reward = max_reward × passed_verifiers / total_verifiers**

每项固定注册verifier等权。reward保留6位小数，使用十进制ROUND_HALF_UP；始终另外保存整数通过数/总数、未加权通过比例和是否全部通过。

例如通过一半验收项：简单题0.5/1，中等题1/2，困难题1.5/3。增加测试数量不会自动提高一道题的满分。当前14+26+16个唯一任务的全量满分为114。

## 2. 什么算一个 verifier

- Medium26和Mixed16 v4：每个既有业务API输入向量计1项；其预期值、异常要求、输入不变要求保持原规则。
- 每个组件已有的加载器/parser/render接口检查合为1个I/O合同验收项，内部条件全部满足才通过。避免将重复的基础JSON检查拆成许多得分项。
- 每个既有业务输出文件计1项，同时检查原本要求的语义、schema及规范序列化。最终core/report同样各计1项；保留原有摘要解释。
- 原14题：沿用已有focused check，每个组件计1项，根集成check计1项。部分旧focused文件只有main函数，评分器会真正调用它，不以脚本空执行成功代替检查。
- 不按Python assert行数、Agent新增检查数或本地check打印的成功条数计分。

`catalog.json`在运行前固定56题的verifier ID、总数和测试描述摘要。不能因缺实现、异常、超时或结果不好而缩小分母；候选添加文件也不能增加可得分项。原14题的验收粒度较粗，分数步长与新任务不同，报告保留这一来源差异。

## 3. 不再首错即停止

各验收项独立运行与记录。一项失败不妨碍其他可执行验收项获得分数。业务API使用原可信输入/上游预期，避免某一缺失分支使所有下游接口都无法诊断；文件集成另有独立验收。

NaN等原有边界检查继续保留。MP04的数组/字典输出要求按既有参考规则判定，不做事后自动转换，也不改写题目或历史分数。规格歧义作为单独评审问题记录；本次变更不声称解决了这些内容问题。

分项报告区分business、domain_validation、robustness、interface、integration。这些分类用于诊断，不额外设置主观类别权重。

## 4. 完整性与异常

篡改/缺失受保护输入、契约、检查器或物化材料，reward强制为0，标记invalid_submission。完整性检查不计可赚取的分数；空工作区不会因为没有篡改文件就得分。LF/CRLF只接受已从同一可信源登记的字节变体。

候选函数异常、缺文件及超时，记相应verifier未通过，分母不变。可信测试/目录/评分器自身损坏属于grader_error，不能伪装成模型的零分。CLI在有效评分（含部分分、零分）时返回0，在评分器错误时返回2。

评分在临时副本中重建输出，保留原答案快照。哈希/进程隔离不是恶意Python的完整系统沙箱；正式运行仍应把评分材料放在Agent不可读写的独立验证环境。

## 5. 使用

在仓库根目录运行：

```bash
python3 evaluation-v2/score.py --benchmark-root . --task medium/MP01 --workspace /path/to/answer --json-output /tmp/score.json --reward-output /tmp/reward.txt
```

其他例子：`original/sdk_compatibility_upgrade`、`hard/identity_federation_transition_spec_v4`。条目见`catalog.json`。

Harbor适配必须读取小数reward文件，不能再用退出码映射为0/1。生成新的外部评测适配包：

```bash
python3 evaluation-v2/build_harbor.py --benchmark-root . --tier medium --output /tmp/medium26-reward-v2
```

导出的TASK及workspace逐文件核对与源相同；改变的是外部tests/test.sh和评分器。默认复用本机实验镜像`pilot10-common:20261031`，可用`--base-image`选择兼容镜像。目录不得覆盖旧实验。

## 6. 报告与比较

每题报告：reward、max_reward、passed_verifiers、total_verifiers、pass_ratio、all_checks_passed、integrity_ok及逐项诊断。

同一固定任务清单下，总分为各题reward之和；标准化总分为sum(reward)/sum(max_reward)。同时报告严格全通过率及分难度的pass_ratio。不能将不同满分的reward均值直接称为准确率。

旧结果与本版本结果标注不同evaluation_version。已有前五题答案只做离线重评分，无新模型请求；旧五题0/1结果没有覆盖。见[离线重评分](review/离线重评分.md)。

## 7. 验收与内容冻结

- [评分规则配置](policy.json)
- [固定验收项目录](catalog.json)
- [1044份原任务文件哈希](task-content-freeze.json)
- [评分器验收报告](review/validation_report.json)

作者复验：`python3 evaluation-v2/qa.py --benchmark-root . --work /tmp/reward-v2-qa`。需要一个新的作者工作目录，不运行模型。
