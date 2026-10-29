# 备份恢复认证：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`products/backup_graph/`、`products/journal_restore/`、`products/backup_windows/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
不得修改README.md、任务说明、inputs/、任何contract.json、check_module.py、根check.py或integrate.py。已有受保护稳定接口保留。

本题初始工作区提供受保护的materialize.py。使用`python3 materialize.py`生成输入、产品契约、局部检查及缺失实现占位；这是材料准备操作，不生成业务答案。脚本校验嵌入清单SHA-256；重复执行保留已有实现并检查受保护生成文件，冲突必须失败。不得改物化器或生成的输入/契约/检查。

## 公共函数接口与输入解释

- `model.load_payload(path: Path)`：读取UTF-8 JSON，对象或数组顶层合法；非法JSON、顶层null/布尔/数字/字符串均抛ValueError。业务字段由transform检查。
- `transform.transform(payloads: list, contract: dict)`：payloads严格按该契约inputs的顺序传入已读取的对象或数组，返回`{"name": contract["name"], "result": 算法结果对象}`。输出恰有name/result两层；本说明各operation的输出字段均属于result，不得额外嵌套一次name/result。不得修改payloads或contract。
- 输入对象仅当键集合恰好是`{"name","result"}`时视为上游组件封装；先读取其result，再使用对应operation约定的字段。原始本地对象不是文件路径，也不当成records或nodes列表。多输入operation必须消费全部指定输入，不能复制固定上游结果。
- `render.build_component(root: Path, contract_path: Path)`：读取该契约及其全部输入，调用transform并返回完整封装；执行组件render.py时写入contract.output。文件路径相对于工作区root；从任意当前目录启动均应正确，缺文件或子命令失败须失败。
- int字段严格排除bool；有限数字允许int/float但排除bool、NaN、Infinity。非空文本先检查去首尾空白后不为空；是否返回去空白/小写形式由各operation明确规定，不全局改写身份字段。列表与字典按规定类型读取，不把null当空集合，不自动把数字字符串转换成数字。
- 文中没有给出默认值的必要字段缺失、非法类型或明确列出的冲突抛ValueError；合法无解使用operation的无解结果，不等同于输入错误。词典序采用通常字符串/列表/元组顺序，相同前缀时较短列表更小。
- contract中的name/operation/inputs/output是接口字段；只有下列业务规则显式使用的算法参数参与计算，不能看到threshold便对所有operation筛选。参数值读取本组件契约，不从样例推断固定常量。

本题强化operation（recovery_chain, restore_join, transaction_replay）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

## 各组件的完整业务规则

### products/backup_graph — 分叉备份链的恢复点与成本优化

operation：`recovery_chain`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {target:int>=0,snapshots:[{id,kind:full/incremental,parent:str或null,start:int>=0,end:int>start,cost:int>=0,epoch:int>=0,valid:bool,state:[{key,value:JSON值}]}]}。snapshot ID与每份state的key唯一，未知parent或任意parent环ValueError。full必须parent=null且start=0；incremental只有parent有效、parent.end==start且epoch相等才可恢复（不满足为不可恢复，不是schema错误）。valid=false的节点及其后代不可恢复；只有end<=target可选。先最大化恢复点end，再最小化整条链cost，再按路径ID列表字典序最小选一条。输出 {feasible,chain:list[id],snapshot_end:int,cost:int,state:按key排序的完整恢复点状态}；无可恢复快照时false/[]/0/0/[]。

补充边界：state表示该快照终点的完整恢复点状态，不是增量patch；最终state直接取所选链末快照的state，不把祖先state再合并进来。链成本是所选路径各快照cost之和。需要检查所有parent分量中的环和未知引用，即使快照invalid或end超过target也不能隐藏schema错误。incremental的parent=null是不可恢复，非full的schema失败；full的非null parent或start!=0才是schema错误。无可恢复快照与可行的空state快照有不同feasible值。

局部检查命令：`python3 products/backup_graph/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/journal_restore — 连续LSN与原子事务重放

operation：`transaction_replay`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {checkpoint:int>=-1,records:[{lsn:int>=0,epoch:int>=0,tx:str,kind:write/commit/abort,...}]}。write含key:str、value:JSON值、seq:int>=0；commit含count:int>=0；abort无额外必需字段。每lsn取最高epoch，任意相同lsn/epoch内容冲突ValueError，相同内容去重；从checkpoint+1连续扫描，首缺口停止。按LSN积累每tx的writes；commit须seq恰为0..count-1，每key可重复并按seq覆盖，之后才一次输出原子事务；缺写commit标为incomplete，不输出部分写。abort丢弃事务。已扫描前缀内commit/abort后又出现同tx记录ValueError。输出 {watermark:int,transactions:[{tx,commit_lsn,writes:[{key,value}],duration:int}],incomplete:list[tx],incomplete_commits:[{tx,commit_lsn}]}；transactions和incomplete_commits按(commit_lsn,tx)，duration为write条数，writes按seq，incomplete含未结束/缺写事务并按tx排序。空records返回checkpoint及空集合。

补充边界：同LSN/epoch冲突检查覆盖全部版本，包括被较高epoch覆盖或位于扫描缺口之后者。事务执行只针对checkpoint后的连续LSN前缀，watermark是实际扫描到的最后LSN，包括abort和不完整commit；不是最后成功commit。已成功commit的writes保留全部按seq排序的写入，包括重复key，不提前压缩成键值表；后续restore应用时才由后写覆盖。seq重复、缺失或越界都属于不完整commit，写入不部分提交。count=0且无写时可以提交零duration事务。缺口后记录不影响pending/ended执行状态，但仍需完成字段与版本冲突校验。

局部检查命令：`python3 products/journal_restore/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/backup_windows — 快照与原子日志的恢复一致性核验

operation：`restore_join`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为 {target:int>=0,rto:int>=0,expected_sha256:64位小写hex}、recovery_chain结果、transaction_replay结果。要求snapshot可行、snapshot_end<=target、日志watermark>=target，且snapshot_end<commit_lsn<=target范围没有incomplete_commits。取该范围的原子事务按commit顺序应用到snapshot.state；不能应用仅有部分writes或aborted事务。耗时=备份链cost+所应用事务duration之和。输出 {feasible,reason:ok/snapshot/gap/transaction/rto/digest,applied:list[tx],state:[{key,value}],sha256:str,cost:int}，state按key；digest为state规范紧凑JSON的SHA256。snapshot/gap/transaction失败输出空applied/state、sha256为空、cost=0；其余失败保留计算结果。失败优先级为snapshot、gap、transaction、rto、digest，不能因目标摘要恰好一致而忽略缺写的已提交事务。

补充边界：base.state为完整起点，事务范围严格是(snapshot_end,target]。按(commit_lsn,tx)应用每个原子事务，内部按其writes给定seq顺序覆盖key，保留未被覆盖的快照键；不能只保留日志键或把snapshot_end这一刻的commit再应用。rto/digest失败时也返回已经计算的applied/state/sha256/cost；snapshot/gap/transaction失败才清空这些字段。无应用事务时仍以快照成本和状态计算摘要并检查rto/digest。

局部检查命令：`python3 products/backup_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`备份恢复认证`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
