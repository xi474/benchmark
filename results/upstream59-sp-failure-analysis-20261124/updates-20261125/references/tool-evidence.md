# 工具比较所用的历史证据与补丁归因范围

<a id="receipts"></a>

## 历史 SP 分支交付和整题复验

历史首轮的 166 份成功文件交付回执均标记为仅核实文件完整性。59 题中，37 题最后一次有限自检通过，其中 19 题正式严格未过。按原有重放策略选取后，对应为 42 题自检通过、21 题正式严格未过。这几类计数的分母分别为交付回执、首轮题位及选定题位。[整题自检逐题数据](../evidence/tool-feedback-audit-20261125.json) · [分支交付及编辑证据](../evidence/historical-patch-opportunities.json)

C055 的历史候选能独立处理若干输入，正式核心转换检查仍漏了同时涉及模板引用、字段遮蔽的组合；N24 的接口需要关注是否原地改变输入，仅比较返回值的自测会漏掉此行为。候选是否已经正确、哪条检查发现错误、修改后是否复验应分别登记。11 月 25 日同事复测的选定结果里，这两题都严格通过，历史案例可用于验证工具能否揭示差异。[历史业务规则和复现](https://github.com/xi474/benchmark/blob/fa3a0f9c040edc422b7e92b5e2bf75d16e4a8720/results/upstream59-sp-failure-analysis-20261124/SP工具与验证机制适配报告.md#contract) · [复测配对](../evidence/nanobot-vs-sp-retest-20261125.json)

<a id="patch"></a>

## 怎样解释“补丁带来 0.4 提升”

这项反馈来自单独一次同事端观察，早先汇总时没有对应的配对清单、采用策略、分母及单位。本次公开的 59 题复测同时改变了多项运行时机制，表中整批工作区 reward 从 85.361619 升至 87.687758。这一变化是整套配置的实测总差。若要估计单个工具的增益，需有同题、同预算、同门控和同重放策略的配对试次，再核实实际工具菜单、选择、改动、复验与交付。[同事复测报告](https://github.com/xi474/benchmark/blob/4fe8cbfa807ba6dda55d836ed5361046c1fdbdb7/results/upstream59-full-retest-v31-20261125/analysis/全量59题benchmark复测报告-20261125.md) · [运行时补丁与后续默认配置说明](https://github.com/xi474/benchmark/blob/4fe8cbfa807ba6dda55d836ed5361046c1fdbdb7/results/upstream59-full-retest-v31-20261125/runtime-patches/README.md)

<a id="tools"></a>

## 四系统工具计数

SP 从首轮模型响应所带工具调用取数，Codex 从原生轨迹步骤取数，DSH 从工具事件流取数，Nanobot 从原生工具启动事件取数。另计工具对模型可见的清单。调用成功、工具进程退出、整题正式通过须查各自的回执；模型同一步选择多个工具与它们的执行时间区间重叠也分别记录。[四系统逐题工具清单](../evidence/four-toolchains-59.json) · [Nanobot 真实调用及结果](../evidence/nanobot-tool-audit-59.json) · [实际重叠的工具区间](../evidence/nanobot-batches-59.json)
