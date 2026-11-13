# 新增30题核心版 v1

30道可运行改编题，94个组件，全部以中等为结构设计目标，实测档位尚未校准。来源：SWE-bench Verified 11、SWE-bench Pro 8、Terminal-Bench 7、GAIA2 4；共31个源实例。保持multistage4、reasoning4、context8、linux2四类组织方式。

## 当前完成情况

- 30/30参考解在Linux中严格通过，典型业务错误解均被拒绝。
- 30/30“核心转换100%但构建器不能独立工作”的控制均不能严格通过，完整性控制均清零。
- 547个核心验收单元已冻结；30个Harbor包已用本机Harbor 0.24.0解析器校验。
- pre1四道代表题已完成Terminus 2＋V4 Pro普通模式单次试跑，均公开及严格通过、Reward=2/2；正式v1五次分档尚未开始。

## 阅读入口

- [逐题来源、原始标签与改编范围](docs/原题来源与改编说明.md)

- [30题目录与实际DAG](docs/30题目录与实际DAG.md)
- [核心验收与改编修订原因](docs/质量验收与改编修订.md)
- [四题Terminus 2试跑结果](docs/Terminus2四题试跑报告.md)
- [作者验收记录](review/author_validation.json)
- [Harbor配置与镜像校验](review/harbor_validation.json)
- [逐题来源及原始难度](review/source_annotations.json)
- [冻结评分清单](verifier/catalog.json)

## 使用

每题位于tasks/结构风格/题目目录，入口TASK.md，工作区workspace/。Agent只接收该题TASK和初始workspace，不接收verifier、_authoring、参考实现或隐藏向量。输出目录会清空重建，源码应保留在组件engine.py或私有源码模块。

```bash
cd tasks/reasoning4/nested_model_dependencies/workspace
python3 check.py
# 正式评分（在可信评测环境中执行）
python3 /path/to/medium30-core-v1/verifier/score.py --package /path/to/medium30-core-v1 --task N01 --workspace "$PWD"
```

另有[Harbor独立包](../medium30-core-v1-harbor.zip)，解压后的30个medium30-v1-Nxx子目录可直接交给Harbor/Terminus 2。其中tests只进入分离验收环境，environment/workspace不含答案。普通模式和模型身份应沿用已审计网关固定并记录，不能仅以模型别名推定。

Harbor包复用本机已安装的pilot10-common:20261031、capstone-terminus-deps:20261105基础镜像，N26另用capstone-medium30-numeric:20261110；实际镜像摘要见review/harbor_validation.json，数值依赖构建配方见review/numeric_Dockerfile。跨主机运行须准备对应镜像；经典TASK/workspace本身只依赖上述Python/Git/NumPy/SciPy环境。

## 评分

沿用[统一评分标准v1.0](https://github.com/xi474/benchmark/blob/main/docs/scoring/统一评分标准_v1.0.md)：分别报告公开通过、核心转换用例通过率、严格通过和Reward。A为逐转换用例，B为每组件接口bundle（含两组干净独立构建），D为组件/额外产物/集成，P为整题公开检查1单元。

`Reward = integrity × 2 × (0.5 × K/N + 0.5 × Strict)`。完整性失败清零，Strict必须P和全部A/B/D通过；不额外增加Strict检查单元。权重2在版本发布前冻结，不随之后观测档位回改。未注册R，可选稳健性显示N/A。

20题的实际组件DAG宽度大于1，其余为串行或组件内分组并行的对照。并行开发机会与运行时数据依赖分别看待，不把模块数量当作难度。

## 再构建

将_authoring复制到独立工作目录，先执行build.py，再执行qa.py。它包含作者实现和私有金标，不能放入Agent工作区。验收环境为Python3.12，与固定镜像一致；作者生成图还需Pillow，N26作者求解另需NumPy/SciPy。源题材料与原始难度保留在review/source_annotations.json；不存在统一继承的上游中等标签。

## 来源文档补充（2026-11-13）

现有30题的[完整中文来源说明](docs/原题来源与改编说明.md)与[可联结JSON/CSV索引](review/source_provenance_v1.json)已补齐。源题共31个，N15为双源组合。此次只补在线文档和元数据，任务、评分、原始source_annotations及历史ZIP保持原字节；历史完整ZIP仍是原发布快照，最新说明以本在线目录为准。
