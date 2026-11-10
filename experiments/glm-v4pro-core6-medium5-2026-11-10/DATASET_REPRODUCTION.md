# Medium26版本与已测Medium5复现指南

更新日期：2026-11-10。本文用于同事对齐任务版本；核对了远端Git对象、发布包和GLM实际冻结清单，没有重新运行模型。

**GLM本轮每套Harness实际跑的是11题：独立Core6 v3六题＋Medium5五题，并未对每套跑完整新版26题。** 六套正式Harness共66个题位。对比报告还复用了同一五题的历史V4 Pro普通模式结果。

## 1. 已跑的五题：请按这份清单取题

**选中：MP01、MP02、MP03、MP05、MP06。** 它们是从保留Medium20中按原MP编号取的前五题，MP04已被排除，所以不是MP01至MP05。五题均属于完整26题v2中与旧v1逐文件一致的20题，没有重新编号。

- **已测 · MP01：可关闭成员的硬/软加权投票**。实验键：`medium/MP01`。
  取题目录：[`medium26-extension-v2/tasks/multistage4/weighted_voting`](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/weighted_voting)；[直接查看TASK.md](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/weighted_voting/TASK.md)。
- **已测 · MP02：单变化轴的数据分片拼接**。实验键：`medium/MP02`。
  取题目录：[`medium26-extension-v2/tasks/multistage4/single_axis_concat`](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/single_axis_concat)；[直接查看TASK.md](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/single_axis_concat/TASK.md)。
- **已测 · MP03：三种挂载格式的离线事实归并**。实验键：`medium/MP03`。
  取题目录：[`medium26-extension-v2/tasks/multistage4/offline_mount_facts`](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/offline_mount_facts)；[直接查看TASK.md](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/offline_mount_facts/TASK.md)。
- **已测 · MP05：跨应用候选并集与相处时长排名**。实验键：`medium/MP05`。
  取题目录：[`medium26-extension-v2/tasks/multistage4/cross_app_contact_ranking`](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/cross_app_contact_ranking)；[直接查看TASK.md](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/cross_app_contact_ranking/TASK.md)。
- **已测 · MP06：取消日程后多渠道通知**。实验键：`medium/MP06`。
  取题目录：[`medium26-extension-v2/tasks/multistage4/calendar_cancel_notify`](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/calendar_cancel_notify)；[直接查看TASK.md](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/tasks/multistage4/calendar_cancel_notify/TASK.md)。

[下载机器可读的五题清单与SHA256](medium5-selection.json)。该清单固定上述顺序，附题面SHA256、发布清单中的workspace树SHA256及实际GLM冻结文件比对数量。

## 2. 下载和测试步骤

固定数据集提交：[`648732fb2b4215f6cb2479830e374139d70f643a`](https://github.com/xi474/benchmark/commit/648732fb2b4215f6cb2479830e374139d70f643a)，位于仓库`main`分支。使用固定提交可避免后续main更新造成版本漂移。

1. 下载[完整26题v2 Agent包](https://github.com/xi474/benchmark/raw/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2-agent.zip)，解压后在`tasks/multistage4/`中只选上述五个目录；不要按文件夹的字母顺序选前五个。
2. 对每题复制一份干净workspace，仅把该题的`TASK.md`和初始`workspace/`交给Harness。保留原始输入/契约，候选代码和运行产物写入独立工作副本。作者DAG、参考解、verifier不作为模型输入。
3. 候选完成后，在候选workspace运行`python3 check.py`做公开检查；正式评分使用与要对比的报告相同的评分版本，并保存原始score、运行标签和usage。
4. 若还要复现GLM的另外六题，另下载[Core6 v3 Agent包](https://github.com/xi474/benchmark/raw/648732fb2b4215f6cb2479830e374139d70f643a/adapted6-core-v3-agent.zip)，使用其中MP04/08/09/10/11/24。不要直接拿完整26题v2的六题替代Core6 v3。

模型条件：本报告GLM为`GLM-5.3`、`thinking.type=enabled`、`reasoning_effort=low`。六套为Nanobot、OpenCode、Codex、DSH、LangGraph、LATTE planning-adapted。模型相同并不代表运行预算/适配版本自动相同；报告保留了修复版OpenCode配置差异。

## 3. 完整26题v2、六题v3分别新在哪里

- [完整26题v2](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2)：20题与旧v1逐文件一致；修订的只有MP04、MP08、MP09、MP10、MP11、MP24。26题ID及目录没有重编号，业务算法、初始输入与契约沿用，六题主要修正公开题面和接口说明。
- [六题规格修订v2](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium6-specfix-v2)：是完整26题v2中上述六题的单独子集，不是新增六道题。
- [独立Core6 v3](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/adapted6-core-v3)：本轮GLM实际使用的六题。进一步区分核心业务验收与可选稳健性；通用的未消费字段非有限值用例移出核心，而真正参与业务的字段合法性仍需通过。核心/可选用例和Strict口径与旧版完整检查不同。
- **目前没有一个统一的“完整26题Core-v3”目录或压缩包。** 想复现GLM的11题，应组合“Core6 v3六题＋上面的不变Medium5”。不能把完整26题v2说成GLM已经全量跑过。

六题v2的具体规格澄清：

- MP04：明确`records`是对象列表及排序规则，消除列表/字典歧义。
- MP08：明确照片输入已按目标年份预筛选，不要求从未规定的字段猜测年份。
- MP09：概要与组件规则统一，写清时段选择、群组并集及评分/价格排序，不再保留不一致的“最贵”等概要要求。
- MP10：明确单一主联系人、guest_count用途，以及`items`/`unavailable`顺序。
- MP11：明确本地任务不验收未提供的装帧信息，叫车提前量按输入字段。
- MP24：明确`professors`已预筛选正式教授，不要求从缺失职称字段再推断。

详见[六题v2修订与来源归因](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/medium26-extension-v2/docs/修订与来源归因_v2.md)及[Core6 v3核心与稳健性重构说明](https://github.com/xi474/benchmark/tree/648732fb2b4215f6cb2479830e374139d70f643a/adapted6-core-v3/docs/核心与稳健性重构说明.md)。这些是本地改编任务的规格/验收澄清，不能据此归咎原始上游任务。

## 4. 为什么同事可能拿到不同题面

数据集新版已上传`main`。截至核对提交，报告所在`results/v4pro-reward-v2-20261108-dataset`分支仍保留`medium26-extension-v1/`，没有同步main的`medium26-extension-v2/`和`adapted6-core-v3/`。**下载结果分支的仓库ZIP，不等于下载新版数据集。**

旧v1与v2六题的公开要求有修订；独立Core6 v3又有核心/可选评分区分，足以造成六题的题面或分数对不上。但另外20题没有换题：若连本文五题的目录/题面也不一致，需要继续核对对方实际目录与commit，不能直接认定原因。

## 5. 任务版本与Reward版本要分别对齐

当前对比报告按独立冻结`delivery-bonus-50-v1-local-migration-r2`对保存提交离线重评，含50%完整交付奖励。**数据集v2/v3、原reward-v2和新版50%交付奖是不同版本轴。** 完整26题包原附的partial_reward脚本不能自动等同于本报告的新评分器。

复现任务可直接取本文公开Agent包；若要精确复现报告的Reward/Strict，还须使用同一冻结评分器与固定验收清单。结果报告公布的评分说明、指标和指纹不等同于已经分发可执行评分器。比较时同时记录任务ID、题面/初始workspace哈希、评分版本和Harness配置，不能只对照MP编号。

本轮文档核对：26题v1/v2逐文件比较、11题实际GLM题面及所有初始workspace文件与公开提交比对、两份Agent ZIP远端HTTP200与SHA256比对均通过。原任务、原attempt、原score及矩阵数值不因本说明改变。
