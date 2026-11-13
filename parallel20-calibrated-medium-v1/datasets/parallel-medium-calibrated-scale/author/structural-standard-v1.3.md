# 项目结构难度标准 v1.3 与实测校准协议

当前暂定实测口径已于 2026-11-07 更新为固定 Terminus 2、DeepSeek V4 Pro 普通模式、每题三次。下文保留 v1.3 的原实验计划供追溯。 [v1.4 当前规则](难度分档_v1.4_DeepSeek三次.md)

结构难度根据公开规格确定，实测难度根据固定基线下的模型通过率确定。逐题保留两个标签，并另记并行机会和 reward。v1.3 的组合规则是本项目的提案，Terminal-Bench 2.0 提供实测分档方法。

## 为什么调整 v1.2

同一批历史矩阵使用 V4 Pro 普通模式和 reward v2，五种 harness 在原始 14 题上记录了 58/70 个满分单元（82.9%），在 Mixed16 v4 上记录了 37/80 个（46.3%）。DSH 分别为 12/14 和 11/16。原 14 题中，v1.2 建议为 H 的四道 `reasoning4` 题合计 18/20 满分，DSH 为 4/4。历史矩阵横跨 harness，旧题的 focused check 与 v4 的 API 向量验收粒度也有差异。正式实测标签按下文的统一基线计算。 [历史运行审计](../reward-v2-v4pro-matrix210-20261104/stage1-completion-audit.json) · [评分粒度说明](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/evaluation-v2/README.md:17)

原始两道 Linux 题的十个历史单元均记录为零，存在已定位的评分器干扰。reward v2 在答案副本中重跑物化脚本，脚本会用占位文件覆盖已实现模块。留存的答案和评分 traceback 可以直接对照。排除这十个受扰单元后，其余十二题的原记录为 58/60 满分。这是对剩余单元的描述统计。两道 Linux 题的正式结果需在能保留提交实现的评分器中复验。 [评分器调用](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/evaluation-v2/score.py:101) · [物化脚本写入](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/tasks/linux2/linux_release_analysis/workspace/materialize.py:7) · [留存答案](../reward-v2-v4pro-matrix210-20261104/stage1-five-harnesses-r2/jobs/reward-v2-pro-stage1-r2-dsh-06-reward-v2-original-linux_release_analysis/reward-v2-original-linux_release__7r6k76a/artifacts/app/products/dependency_impact/engine.py) · [评分失败记录](../reward-v2-v4pro-matrix210-20261104/stage1-five-harnesses-r2/jobs/reward-v2-pro-stage1-r2-dsh-06-reward-v2-original-linux_release_analysis/reward-v2-original-linux_release__7r6k76a/verifier/score-v2.json)

四道原始求解题的容量单位是**任务名额**，候选边给出可相加的得分和成本。筛掉技能不符的边后，全量指派可归约为标准的带容量二部匹配或最小费用流，再按公开规则处理目标和稳定平局。逐题枚举验证了已发布的四个主用例。每个主用例有 4 个任务和 4 名人员，技能过滤后有 16–24 种候选组合，满足容量的有 5–9 种。四题共用同一个 3×3 公开额外用例。公开输入规模是辅助证据，规格没有规定这就是最大规模。此前 Q24 反例中的时长容量已按原规格纠正。 [原题规格](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/tasks/reasoning4/dependency_release_reasoner/workspace/README.md:10) · [公开用例](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/tasks/reasoning4/dependency_release_reasoner/workspace/engines/maintainer_assignment/check_module.py:13) · [v1.2 逐题报告](../benchmark-structure-audit-20261105/56题ASCI结构难度逐题重审.md)

## v1.3 结构判定

评审依据为公开题面、可见契约和真实业务数据流。每个高档轴都记录必要条件、发生影响的模块和最小反例。题面与验收有实质歧义时先记规格待裁决。

- **A 算法。** A0 是直接转换、筛选或排序。A1 是范围明确的标准算法，包括区间动态规划、图遍历、带容量单位需求的指派，以及彼此独立的标准求解器。精确答案或多级平局本身不足以作为 A2 证据。A2 需要给出额外的语义约束，说明哪种标准简化会产生不合法的结果或错过最优解。例如不可拆分的非单位资源用量、跨候选组的预算与仲裁，或同时作用于同一决策的释放时间和共享资源限制。
- **S 业务状态。** S0 是静态快照上的计算。S1 是有限提交、幂等、回退或检查点推进。S2 要指出至少两种状态规则怎样在同一段合法历史中相互影响，并展示相同当前请求在两段历史下产生不同结果。
- **C 依赖耦合。** C0 是独立任务后汇总。C1 是按固定契约消费上游产物。C2 要求真实的上游结果改变下游候选可行域，或跨阶段必须共同维护同一项业务不变量。用两个合法上游结果构造对照。固定工作流的文件边与组件 API 的附加能力分别登记。
- **I 接口集成。** I0 是固定单接口。I1 是明确的格式或字段规范化。I2 需要有跨版本、协议或后端仍必须保真的业务语义，并举出局部转换虽符合格式却违反整体语义的例子。统一 JSON 外壳和一般序列化只按其实际业务约束判断。

结构档位按条件组合确定。

1. **H** 要求核心需求满足新版 A2，或同一因果链同时有 S2 和 C2 的证据。
2. **E** 可以包含局部 A1。要求 S0、C0、I≤1，且每个必要决策可独立完成；例如互相独立的标准解析、递归配置合并或格式转换。
3. **M** 指范围清楚的联合选择、有限状态或实质汇合。单个标准算法若包含共享资源竞争，仍可为 M。
4. 单个高档轴且尚未命中 H，或评审者对可行域是否被改变有分歧，记为边界待复核。记录分歧的条款和需要补证的反例。

试判中，原四道 `reasoning4` 题建议 **A1/S0/C0/I0，结构 M**。MP02 的有限索引与装配汇合仍是结构 M。Mixed16 v4 的搜索索引重建须从恢复出的合格副本中同时满足独立主机仲裁和总预算，两个同主机副本即使都通过摘要检查也凑不成 quorum=2，因此有结构 H 的直接证据。其余条目需要按同一门槛逐题复核。 [MP02 规格](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/medium26-extension-v1/tasks/multistage4/single_axis_concat/workspace/README.md:55) · [索引切换规格](C:/Users/horac/Desktop/硕士/capstone/previous_benchmarks/xi474-benchmark/mixed16-precise-spec-v4/tasks/context8/search_index_rebuild_spec_v4/workspace/README.md:54)

## Terminal-Bench 式实测校准

Terminal-Bench 2.0 固定 Terminus 2，依据所选模型的逐题通过率划分实测难度，并与设计时的难度标签分别报告。本项目拟采用同样的双标签设计，以及约三分之一、三分之二的两条分界。 [Terminal-Bench 2.0 正式论文 §4.2](https://proceedings.iclr.cc/paper_files/paper/2026/file/444a3737adaee10d86ad2ef5f74468e6-Paper-Conference.pdf#page=7)

1. **先冻结质量口径。** 确认参考解能通过、典型错误解会失败、其他满足规格的解可以通过。先处理 56 题审计的规格争议。把公开要求与正式检查逐项对应，尤其核查三批 verifier 的覆盖差异和反复导致严格失败的共享条款。原始 Linux 两题要先用留存答案复验，确认评分前后候选实现的文件哈希一致。
2. **固定运行基线。** 同一个 harness 和同一套提示、工具、并发方式、初始环境、有效时间及 token 预算。首轮拟用两个不同模型家族，各做 3 次独立运行。模型身份和预算在开跑前登记，按题族预留后续验证题。首轮可抽 18 题，按来源和结构档分层，并记录代表了哪些任务族。该配置对应 108 次有效运行。
3. **以整题通过率定实测档。** 对模型等权，逐题报告各模型的通过次数与有效次数。以整题严格验收为准，基础设施故障单列，已生效的任务预算内失败和超时计为未通过。有效运行满额后，平均通过率达到 2/3 为实测 E，达到 1/3 但低于 2/3 为实测 M，低于 1/3 为实测 H。六次有效运行下分别对应 4–6、2–3、0–1 次通过。部分分与失败类型作为诊断数据单列。
4. **检查两套标签是否一致。** 逐题同时列结构档、基线实测档、模型分项通过数和证据。对临界题与模型间分歧保留原始计数，首轮视为初步校准。发现系统性偏差时先区分规格、验收覆盖与真实能力差异，再到按题族留出的题上复核。

论文方法部分分别交代本项目如何定义 A/S/C/I、结构档用什么证据审核、实测标签依赖哪组基线，以及两者不一致时如何呈现。`1:2:3` 是独立的 reward 聚合政策。
