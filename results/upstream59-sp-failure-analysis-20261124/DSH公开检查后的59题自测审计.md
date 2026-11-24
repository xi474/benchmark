# DSH 在公开检查通过后怎样自测

Upstream59 · DeepSeek V4 Pro 普通模式 · 2026 年 11 月 24 日离线核验。每题采用矩阵选定的一个原生试次。30 道 C/MS 题为 v2.1 实跑，25 道 MP 题沿用历史解答并离线重评分，4 道 N 题沿用 v2.0 试次。

59 题中，53 题可在原生流中定位首个整题公开通过结果，之后有 45 题实际运行自造业务用例。2 题由新例首先暴露实现错误，修改后同一业务输入复验通过。全批严格通过 36/59（61.0%）。

| 运行时观察 | 题数 | 正式严格通过 | 新例发现实现缺陷并同例修复 |
|---|---:|---:|---:|
| 执行新业务用例 | 45 | 33/45（73.3%） | 2 |
| 仅新造通用读取接口用例 | 3 | 1/3（33.3%） | 0 |
| 仅复核已有公开输入或产物 | 5 | 2/5（40.0%） | 0 |
| 未观察到运行中整题公开检查通过 | 6 | 0/6（0.0%） | 不适用 |

在 5 道只复核已有公开输入的题中，C007、C056、MS14 重跑给定输入或不同入口（严格 0/3）。MP17、MP23 还独立核算旧公开产物的编码或摘要（严格 2/2）。

<a id="source-line-16"></a>
## 两个可核验的修复

- MS02 用两个主题争用同一篇论文，预期无解，实际递归解包 None 出错。第 89–90 行运行并看见失败，第 94 行修改业务代码，第 98–99 行同输入返回 None。正式严格通过。
- MP15 构造模块导入 os、函数内将 os 赋为 1 再返回的程序。第 228–229 行结果错误地把全局导入标成已使用，第 238 行修正作用域扫描，第 242–243 行以原程序复验。正式严格通过。

<a id="source-line-21"></a>
## 实际发出的验证指令

任务启动模板（59/59 个归档根会话有此文字）

> Complete the task in the current /app workspace and run relevant checks.

Agent Team 系统提示的相关片段（59/59 个归档根会话有此文字）

> coordinate them explicitly and have the Lead review the final diff and run tests.

Bash 工具系统提示（59/59 个归档根会话有此文字）

> Check the [exit code: N] marker on every bash result; investigate failures before moving on.

[Agent Team 提示源码](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/experimental/tool-agent-team/src/index.ts#L39) · [Bash 提示源码](https://github.com/horacezoe/CodexAndDSH-/blob/c31818a6f5581ff86b42619a71c4fc391a84ee1f/upstream/packages/shell/tool-bash/src/index.ts#L254)

启动模板来自实验包装层；后两条来自 DSH 系统提示。Agent Team 中的 them 指 Bash、格式化工具、代码生成器和脚本。Bash 提示要求逐次查看退出码、遇错先调查。三条文字均未规定公开检查通过后必须构造反例。

MS02 提供了时序证据。题面规定每个主题选一篇、不得重复使用论文、没有完整分配时返回 null。第 80 行整题公开检查通过；第 88 行是模型主动提出测无解情形，第 89 行通过 Bash 执行。该根会话只有启动时的一次系统消息，41 次工具调用中没有 finish_task，第 138 行才给出最终答复。

## 统计口径与归因

以解题期间整题公开检查命令及相应的明确成功输出为界。只输出结果、只过组件、仅看到评分阶段 P/public 或只在计划中提到要测，都不足以建立此时间界线。6 道缺少界线的题仍保留其正式严格结果。

新业务用例包括调用实际业务代码并能核对预期的自造输入、公开输入的业务变形、与独立参考的差分测试。这里的“举反例”是尝试提出能区分正确与错误实现的用例，其中也有一次通过的用例。只改文件路径或对同一输入更换入口归入公开复核。只自造非法 JSON、NaN 或标量来测通用读取器单列；输入校验若在实际业务变换中检验领域规则，计入业务组。各题只进入一个组，按业务用例、通用接口新例、已有输入复核的顺序归类。

修复须由新输入首先暴露实现与预期的不符，并有业务实现修改及原输入复验成功的事件。修测试期望、修探针、回看已有产物找到问题、只加测试未改实现，以及优化后由公开样例先发现的回归均另记。业务输出与预期不符即算观察到失败，无须进程非零退出。未观察到完整证据不能解释为没有潜在缺陷。

严格通过采用冻结的题位结果。公开检查的现场状态与正式评分时提交的文件、完整性和隐藏用例是不同观察。各组由运行行为事后划分，样本量与题型不同，组间比例不支持因果归因。

## 逐题证据

行号按归档 ZIP 内 agent/dsh-stream.jsonl 从 1 起计。每行链接为该题冻结的原生证据包。

| 题目 | 公开通过行 | 分类 | 执行证据行 | 原例复验闭环 | 正式严格通过 | 解读 |
|---|---:|---|---|---|---|---|
| [C007](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C007.zip) | 87 | 仅复核已有公开输入或产物 | 91, 100 | 未观察到 | 否 | 只复跑原组件、公开整题流程，并读取已有输出长度。 |
| [C008](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C008.zip) | 79 | 执行新业务用例 | 97 | 未观察到 | 是 | 改 seed、时间窗和租户，断言指定两条记录 token 相同、另一条不同，98 行通过。正式成绩采用归档提交离线复评分。 |
| [C009](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C009.zip) | 104 | 执行新业务用例 | 122, 126, 131, 136, 141, 146 | 未观察到 | 是 | 自造取消、连续工时和字典序样例；127 行断言失败，130–137 行确认测试误把利润 7 写为 10，改期望后通过。 |
| [C011](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C011.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 解题阶段仅浏览任务，原生流 72 行 max-tokens，未运行整题公开检查。 |
| [C017](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C017.zip) | 77 | 执行新业务用例 | 86 | 未观察到 | 否 | 组合新联系人补全、冲突回滚、重复记录。87 行打印结果，90 行核对跨批回滚与晋升。 |
| [C031](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C031.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 106–107 行运行公开检查因真实 PTY 权限失败；173–184 行另造管道测试，但发生时未出现整题公开绿。 |
| [C033](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C033.zip) | 122 | 执行新业务用例 | 193, 211, 239, 248, 257, 266, 270 | 未观察到 | 是 | 公开检查曾暴露寄存器问题，118 行修实现、122 行首次公开绿。此后构造 ELF 指令及 I/O 程序；失败涉及测试头长度、跳转夹具布局和寄存器期望，未观察由这些新测试触发的实现修复。最终试次触及预算终止，正式评分另存。 |
| [C039](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C039.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 只做文件和解释器版本检查；26 行因模型流中的工具参数 JSON 无效而结束。 |
| [C049](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C049.zip) | 99 | 执行新业务用例 | 108, 113 | 未观察到 | 否 | 较大网络、多微批与有限差分对照，109 行因测试脚本索引越界，112–114 行调整测试索引后二者吻合。公开绿以前曾修组件。 |
| [C055](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C055.zip) | 70 | 执行新业务用例 | 74, 79 | 未观察到 | 是 | 构造保留/解封标签、别名与模板、锚点快照及覆盖。75、80 行返回自测结果。 |
| [C056](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C056.zip) | 88 | 仅复核已有公开输入或产物 | 92, 96 | 未观察到 | 否 | 复跑公开组件合并和整题，并将已有结果与 public_expected.json 展示比对。正式冻结评分的完整性与解题公开检查独立。 |
| [C058](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C058.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 在分析阶段结束，69 行 turn_end 为 max-tokens；没有整题公开通过事件。 |
| [C062](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C062.zip) | 82 | 执行新业务用例 | 91, 96, 101 | 未观察到 | 否 | 构建刷新合并、在途取消、多存储交错事件，检查各阶段状态。正式冻结评分完整性失败。 |
| [C066](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C066.zip) | 72 | 执行新业务用例 | 81 | 未观察到 | 是 | 自造同一 LSN 重放、终止后重试、事务等变体，从真实 transform 的结果核验。 |
| [C067](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C067.zip) | 78 | 执行新业务用例 | 87, 92, 97 | 未观察到 | 是 | 自造授权失败、找不到服务和路由场景。88、93 行断言失败；91、96 行核对发现测试给错权限预期及查询次数，无业务实现修改。 |
| [C068](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C068.zip) | 82 | 执行新业务用例 | 91, 96, 101 | 未观察到 | 是 | 构造取消、错误缓存、同时加载等。92 行 KeyError 源于测试让输入结束时仍有未完成请求，违反题面前提；95–97 行补推进时间事件，修改了输入。 |
| [C069](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C069.zip) | 112 | 执行新业务用例 | 125, 130, 135, 140 | 未观察到 | 是 | 构建续签、到期、回退和跨阶段产物等场景；146、151 行的异常是入口测试误用 json.loads 读取文件，154–155 行纠正测试。 |
| [C074](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C074.zip) | 62 | 执行新业务用例 | 66, 71, 76 | 未观察到 | 是 | 自造忽略项、文件与目录在两次扫描中互换、嵌套完成等输入，67、72、77 行返回结果。 |
| [C077](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C077.zip) | 88 | 执行新业务用例 | 96, 101, 110 | 未观察到 | 否 | 自造重叠修改、重试时仍有在途操作、定时器与同一时刻事件的次序。 |
| [C079](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/C079.zip) | 74 | 执行新业务用例 | 88, 92, 97, 102 | 未观察到 | 是 | 构造损坏后重试、重试耗尽、缩略图、空文件、非零 nonce 与递增；实际断言通过。 |
| [MP01](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP01.zip) | 91 | 仅新造通用读取接口用例 | 100, 105 | 未观察到 | 是 | 另造 NaN、Infinity、标量与损坏 JSON，检验通用 load_payload；复算公开清单哈希并更换工作目录。 |
| [MP02](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP02.zip) | 115 | 执行新业务用例 | 124, 129 | 未观察到 | 是 | 以冲突记录测试 first 和 drop_conflicts；首次探针导入错 transform，修正探针后通过。 |
| [MP03](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP03.zip) | 124 | 执行新业务用例 | 142, 147, 152, 162 | 未观察到 | 否 | 自造 fstab 解析、冲突和非冲突条目及缺字段；首次导入缓存串模块，隔离探针后通过。 |
| [MP04](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP04.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 轨迹止于列目录与规划；找不到整题公开检查的通过输出。 |
| [MP05](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP05.zip) | 152 | 执行新业务用例 | 174, 184 | 未观察到 | 否 | 第184行构造非常规联系人年龄。另在156–157行复看公开产物，从日历重复出席者时长发现业务缺陷；161行修复，165–166行原公开数据复验。 |
| [MP06](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP06.zip) | 151 | 仅新造通用读取接口用例 | 165 | 未观察到 | 否 | 新造 NaN、无穷和顶层标量，测试通用 load_payload。公开通过前曾有导入路径错误。 |
| [MP07](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP07.zip) | 120 | 执行新业务用例 | 139, 149 | 未观察到 | 是 | 构造回执失败阻止归档的输入及 attention 分支，核验对应动作和标记。 |
| [MP08](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP08.zip) | 93 | 执行新业务用例 | 107, 117, 122, 127 | 未观察到 | 是 | 构造分类、缺失路径和碰撞用例；一次测试导入名错误，纠正探针后继续。 |
| [MP09](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP09.zip) | 119 | 执行新业务用例 | 137, 142, 147, 149, 154, 159 | 未观察到 | 是 | 测试忙碌时段、分组不全、库存不可用及提交/循环条件；隔离模块导入后检查完成。 |
| [MP10](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP10.zip) | 110 | 执行新业务用例 | 136, 141, 148, 150 | 未观察到 | 是 | 构造同一星期几、库存不足及小时格式等边界。 |
| [MP12](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP12.zip) | 144 | 执行新业务用例 | 186, 190, 194, 199 | 未观察到 | 否 | 构造路径冲突、大小写邮件、非法日期、错误发件人、提交冲突。各次探针当时按预期通过；后续根据规格重新解释空关键词并修改，未见新用例失败后按原例复验。 |
| [MP13](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP13.zip) | 116 | 执行新业务用例 | 142 | 未观察到 | 是 | 构造重复 ID、词汇及非法浮点时间；另有在其他目录运行时缺前置产物的检查。 |
| [MP14](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP14.zip) | 105 | 执行新业务用例 | 116, 121, 126 | 未观察到 | 是 | 构造链式抑制与嵌套帧。116行把接口接受数组打印为 FAIL，随后核对约定并改正预期。 |
| [MP15](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP15.zip) | 204 | 执行新业务用例 | 223, 228, 242, 257, 277, 287 | 是 | 是 | 228–229行用模块 import os、函数内 os=1 并 return os 暴露局部遮蔽误判；238行改动分析器；242–243行复跑相同程序和普通引用，恢复未使用全局导入的预期。 |
| [MP16](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP16.zip) | 138 | 执行新业务用例 | 152, 162, 167, 172 | 未观察到 | 是 | 构造无法解析的定义、签名、继承和类型限定等业务边界。 |
| [MP17](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP17.zip) | 115 | 仅复核已有公开输入或产物 | 124, 129, 134 | 未观察到 | 是 | 核对原 MIME 消息与同一份公开的 0x00–0x7f 载荷的 base64 折行，复跑原组件和整题。 |
| [MP18](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP18.zip) | 116 | 执行新业务用例 | 130, 135 | 未观察到 | 是 | 构造清单冲突、过滤等边界；校正对公开输出长度的手工估计。 |
| [MP19](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP19.zip) | 127 | 执行新业务用例 | 150, 159 | 未观察到 | 是 | 自造两个 from-import 子模块解析场景，再测外部允许列表和别名。 |
| [MP20](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP20.zip) | 106 | 执行新业务用例 | 115 | 未观察到 | 是 | 自造悬挂分段以及非法 JSON，检查相应解析/校验行为。 |
| [MP21](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP21.zip) | 107 | 执行新业务用例 | 116, 126 | 未观察到 | 是 | 另造三首曲目的播放列表，同时验证算出的整数总时长为4及其类型。 |
| [MP22](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP22.zip) | 181 | 执行新业务用例 | 213, 217, 222, 226, 252, 272, 277, 282 | 未观察到 | 否 | 新造 MARC XML、880 替代题名、DOCTYPE。孤立导入失败及 payload 维度错误属于探针设置；可证业务错误源于189–190行复看公开 subjects 输出，194行修复，198–199行复验公开样例。 |
| [MP23](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP23.zip) | 106 | 仅复核已有公开输入或产物 | 120, 124, 129, 134, 138 | 未观察到 | 是 | 独立从同一公开 core_manifest 复算 SHA，切换目录回放公开输入和整题，另查看源码硬编码。 |
| [MP24](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP24.zip) | 150 | 仅新造通用读取接口用例 | 169 | 未观察到 | 否 | 新造标量、非法常数、无穷与数组测试通用 load_payload，业务输出复用公开数据。 |
| [MP25](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP25.zip) | 102 | 执行新业务用例 | 115 | 未观察到 | 是 | 构造业务负例与新金额，调用相应 transform 验证。 |
| [MP26](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MP26.zip) | 163 | 执行新业务用例 | 182, 187 | 未观察到 | 否 | 自造日期、重复或未知出席人、非法日期，校验日历业务；未构造同日晚八点场景。 |
| [MS02](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS02.zip) | 80 | 执行新业务用例 | 89, 98, 103, 108 | 是 | 是 | L89 构造两主题争用一篇论文，预期无解，实际解包 None 抛 TypeError；L94 改 integration.py 的递归，L98–99 同输入返回 None。随后另测字典序和无效章节。 |
| [MS11](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS11.zip) | 80 | 执行新业务用例 | 89, 94, 104, 182, 196 | 未观察到 | 是 | L89 起随机业务差分、平局和多块配对。L94 对拍的 list/tuple 差异及 L182 的 NameError 是测试程序问题。优化后新引入的业务回归先由原公开检查 L133–134 揭露，L155–164 缩小定位、L168 修复、L172–173 复验，未算新反例首发。 |
| [MS12](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS12.zip) | 104 | 执行新业务用例 | 113, 117, 127 | 未观察到 | 否 | L113 缩小公开样本预算检验无解；L117 构造对称菜单、L127 构造偏好冲突检验最差组优先，通过后无业务修复。接合结果格式修复在首绿前。 |
| [MS14](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS14.zip) | 77 | 仅复核已有公开输入或产物 | 81, 86 | 未观察到 | 否 | L81–82 重跑给定组件与合并流程。L86–87 用同一 public_input.json 调用 transform 和换路径的 build_component，将两次结果与公开期望比对。 |
| [MS23](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS23.zip) | 79 | 执行新业务用例 | 88, 98, 103, 152, 157, 181 | 未观察到 | 否 | L88–94 新随机枚举对拍产生不一致，核对后修独立穷举器的重复计数。L103 测冲突约束，L181 再做随机对拍。首个公开通过前 L74 修过业务实现。本行门槛据原生执行，非事后离线分数。 |
| [MS28](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS28.zip) | 62 | 执行新业务用例 | 71, 76, 81, 86, 91, 106 | 未观察到 | 是 | L71–91 构造单项、并列峰值、互不相交组件及其最大比；L76 后的手算疑点用子集枚举复核，未改业务实现。L106 构造 14 项规模验证。 |
| [MS29](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS29.zip) | 62 | 执行新业务用例 | 70, 75, 80 | 未观察到 | 是 | L70 构造库存覆盖、无可行计划、空需求和多菜品；L75 构造生产循环与链条；随后核对最短步骤的字典序，过界后未修改业务实现。 |
| [MS30](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS30.zip) | 60 | 执行新业务用例 | 69, 74, 79, 84, 89 | 未观察到 | 否 | L69–90 分别验证强制配对、严格偏好阻塞、同档平局、独立组件合并与有限容量，均有具体预期，未触发实现修复。 |
| [MS41](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS41.zip) | 58 | 执行新业务用例 | 66, 71, 76, 81, 85 | 未观察到 | 是 | L66 在工作区成功运行环状合成例；L71–86 对拍与手算。初始导入路径、参考程序成本公式和随机生成器空集报错属于自测代码。业务实现未改。 |
| [MS42](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/MS42.zip) | — | 未观察到运行中整题公开检查通过 | — | 不适用 | 否 | 读取公开检查器源码 L25，未执行整题检查；L68 结束，原终态 NonZeroAgentExitCodeError。单独保留。 |
| [N11](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/N11.zip) | 71 | 执行新业务用例 | 80 | 未观察到 | 是 | L80–81 自造分块的 3×3 稠密矩阵，用单独实现的稠密乘法对比分块立方并 assert。L61–66 公开样例相关修复在首绿前。 |
| [N17](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/N17.zip) | 62 | 执行新业务用例 | 71 | 未观察到 | 是 | L71 第一套模板是公开输入，第二套新造乘法、多个属性前缀、条件表达式、嵌套下标，L72 实际返回依赖列表。L76 另换路径跑公开样例。 |
| [N22](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/N22.zip) | 143 | 执行新业务用例 | 210, 214 | 未观察到 | 是 | L210 新建含嵌套目录的替代仓库，L214–215 对包装层、定位和恢复运行新样例。此前增强二进制处理、路径兼容源于读代码和预判，无新例先失败证据。 |
| [N24](https://github.com/xi474/benchmark/blob/00d32858637689c0668c71303d4d5b79d00b1093/results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123/dsh/N24.zip) | 76 | 执行新业务用例 | 85, 90 | 未观察到 | 是 | L85 构造卖方非所有者应拒绝及真正所有者应接受。L86 报错因自写断言少算空格，L89–91 改测试预期，未改业务实现。 |
