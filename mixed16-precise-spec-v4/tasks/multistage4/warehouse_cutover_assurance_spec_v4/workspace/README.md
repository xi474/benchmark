# 数仓切换保障：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`domains/backfill/`、`domains/freshness/`、`domains/checksums/`、`views/cutover_risk/`、`views/reviewer_load/`、`views/repair_waves/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
不得修改README.md、任务说明、inputs/、任何contract.json、check_module.py、根check.py或integrate.py。已有受保护稳定接口保留。

## 公共函数接口与输入解释

- `model.load_payload(path: Path)`：读取UTF-8 JSON，对象或数组顶层合法；非法JSON、顶层null/布尔/数字/字符串均抛ValueError。业务字段由transform检查。
- `transform.transform(payloads: list, contract: dict)`：payloads严格按该契约inputs的顺序传入已读取的对象或数组，返回`{"name": contract["name"], "result": 算法结果对象}`。输出恰有name/result两层；本说明各operation的输出字段均属于result，不得额外嵌套一次name/result。不得修改payloads或contract。
- 输入对象仅当键集合恰好是`{"name","result"}`时视为上游组件封装；先读取其result，再使用对应operation约定的字段。原始本地对象不是文件路径，也不当成records或nodes列表。多输入operation必须消费全部指定输入，不能复制固定上游结果。
- `render.build_component(root: Path, contract_path: Path)`：读取该契约及其全部输入，调用transform并返回完整封装；执行组件render.py时写入contract.output。文件路径相对于工作区root；从任意当前目录启动均应正确，缺文件或子命令失败须失败。
- int字段严格排除bool；有限数字允许int/float但排除bool、NaN、Infinity。非空文本先检查去首尾空白后不为空；是否返回去空白/小写形式由各operation明确规定，不全局改写身份字段。列表与字典按规定类型读取，不把null当空集合，不自动把数字字符串转换成数字。
- 文中没有给出默认值的必要字段缺失、非法类型或明确列出的冲突抛ValueError；合法无解使用operation的无解结果，不等同于输入错误。词典序采用通常字符串/列表/元组顺序，相同前缀时较短列表更小。
- contract中的name/operation/inputs/output是接口字段；只有下列业务规则显式使用的算法参数参与计算，不能看到threshold便对所有operation筛选。参数值读取本组件契约，不从样例推断固定常量。

### 证据公共字段

证据公共字段：每条输入均含id:非空str、revision:int>=0、owner:非空str、category:prepare/copy/verify、tags:list[非空str]、failures:int>=0、total:int>=1、lag:int>=0、valid:bool；failures<=total。所有整数排除bool。id去首尾空白；owner/category/tags去空白小写；tags去重排序。先校验全部记录与修订冲突，再取最新版本。只有本operation段落指定的公式决定score，其他operation的公式不适用。

## 各组件的完整业务规则

### domains/backfill — 修订证据失败率

operation：`failure_evidence`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入为记录数组。每项必须有 id:非空字符串、revision:整数>=0、owner:非空字符串、category:prepare/copy/verify、tags:字符串数组、failures:整数>=0、total:整数>=1、lag:整数>=0、valid:布尔；failures<=total。id去首尾空白；owner/category/tags去首尾空白并小写；tags去重排序。先校验每个输入版本，再按规范化id选最大revision。同id同revision的全部规范化字段必须相同，否则ValueError；相同副本去重，即使该版本不是最新版也检查冲突。评分仅为 ceil(20*failures/total)+offset，再截断到[0,20]。不使用lag、sla或valid计算本operation的评分。输出result={records:[{id,source,owner,tags,category,score}],count,score_total}；source=contract.name，records按(source,id)升序，count为最新记录数，score_total为这些记录分数之和。threshold不筛除证据记录。空输入records=[]，count=score_total=0。

局部检查命令：`python3 domains/backfill/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### domains/freshness — 修订证据延迟

operation：`lag_evidence`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

记录字段、规范化、全部修订的冲突检查、最新版选择和输出字段与本说明中的证据公共规则一致：id去空白；owner/category/tags去空白小写，tags去重排序；所有版本均校验，按id保留最大revision；相同id/revision规范化内容不一致报ValueError。每条记录仍必须包含failures、total、lag、valid等全部证据字段且满足类型/范围约束。评分仅为ceil(lag/sla)+offset，再截断到[0,20]，sla为契约中的正整数。不把失败率公式叠加到延迟公式上，不用threshold筛除证据记录。result={records:[{id,source,owner,tags,category,score}],count,score_total}，source=contract.name，records按(source,id)排序。空输入为空records及两个零统计。

局部检查命令：`python3 domains/freshness/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### domains/checksums — 修订证据完整性

operation：`integrity_evidence`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

记录字段、规范化、全部修订的冲突检查、最新版选择和输出字段与本说明中的证据公共规则一致：id去空白；owner/category/tags去空白小写，tags去重排序；所有版本均校验，按id保留最大revision；相同id/revision规范化内容不一致报ValueError。每条记录仍必须包含failures、total、lag、valid等全部证据字段且满足类型/范围约束。评分仅为(0 if valid else 15)+failures+offset，再截断到[0,20]；不使用ceil(20*failures/total)或延迟公式。不用threshold筛除证据记录。result={records:[{id,source,owner,tags,category,score}],count,score_total}，source=contract.name，records按(source,id)排序。空输入为空records及两个零统计。

局部检查命令：`python3 domains/checksums/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### views/cutover_risk — 风险排名

operation：`risk_ranking`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入为按契约inputs顺序传入的组件封装；对每个封装读取result.records。以(source,id)合并：键相同且整条记录相同才可去重，否则ValueError。设合并集合为R，先选score>=threshold，再按(-score,source,id)排序，最后截取前limit项得到S。result.records、ranking、score_total全部基于同一个S，不能让records保留整个R。records仅改变展示顺序，按(source,id)升序；ranking按上述分数排名输出完整source+":"+id；score_total=sum(S.score)，不对R求和。输出result恰为{records,ranking,score_total}；S为空时分别为[]、[]、0。不得丢弃source前缀或再次按id跨source合并。

局部检查命令：`python3 views/cutover_risk/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### views/reviewer_load — 负载分配

operation：`review_balance`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

合并每个输入封装的result.records，以(source,id)去重，相同键内容冲突ValueError。使用全部合并记录，不再应用threshold、limit或其他筛选。按(-score,source,id)逐条处理，每次选当前累计score最小的reviewer，平局取reviewer名称字典序最小者；加入该记录score。reviewers来自本组件契约，不能只保留最终被分配到任务的人。result={records,assignments,loads}；records按(source,id)；assignments是{id:完整source+":"+id,reviewer}并按id排序；loads包含所有reviewer（包括零负载）。空输入仍返回完整零loads，其余两个列表为空。

局部检查命令：`python3 views/reviewer_load/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### views/repair_waves — 依赖波次与条件修复

operation：`remediation_plan`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入是组件封装，不是原始nodes数组。合并所有输入的result.records，包括审核分配组件返回的records；以(source,id)去重，相同键整条记录冲突ValueError。只读取records，不使用assignments、loads或feasible推导人员边、job/worker匹配或额外阻断。only_if_blocking=false时保留全部合并记录；为true时，若存在至少一条tags含blocking且score>=threshold的记录，也保留全部记录；否则使用空记录集合。此开关不是逐条筛选器。对保留集合，每条记录对应一个业务节点，完整id为source+":"+id，duration=1+score//5；category次序prepare<copy<verify，每个节点依赖集合中所有严格较早类别节点。按下述业务图规则计算waves/earliest_finish/critical_path/makespan：每波取本波开始时所有依赖已提交的节点并按id排序，整波结束后才取下一波；finish=duration+最大前驱finish，无前驱为duration；最大finish并列时，先比较前驱已经形成的完整路径列表（尚未追加当前节点）并取字典序最小，再追加当前节点；最终终点按finish最大、完整路径字典序最小选择。result={records,blocked:false,waves,critical_path,makespan,earliest_finish}；records按(source,id)，earliest_finish键按id。空集合时records/waves/critical_path=[]、makespan=0、earliest_finish={}、blocked仍为false。该业务图规则不表示Agent应怎样拆分或调度任务。

局部检查命令：`python3 views/repair_waves/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。
已有`python3 integrate.py domains`是一个数据转换接口：读取domains组件结果，按(source,id)合并records，冲突报错，写`outputs/domain_core.json`。只有现有契约实际引用该文件时才需要此产物；不要无条件增加接口中不存在的业务输入。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`数仓切换保障`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
