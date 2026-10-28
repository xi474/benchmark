# 备份恢复认证

物化工具并选择最优恢复链，原子重放事务以核验目标状态和恢复时限。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

## 不可修改文件

README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。

## 组件接口

契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。

- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。

- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。

- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。

context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。

## 各组件规则

本任务所有输入中的嵌套JSON值也必须合法；NaN/Infinity在未参与计算的字段中同样应抛ValueError。下游必须实际消费所有契约inputs，不能使用固定的上游副本。

### products/backup_graph — 分叉备份链的恢复点与成本优化

输入：`inputs/backup_graph.json`；输出：`outputs/backup_graph.json`。参数以本组件 contract.json 为准。

输入 {target:int>=0,snapshots:[{id,kind:full/incremental,parent:str或null,start:int>=0,end:int>start,cost:int>=0,epoch:int>=0,valid:bool,state:[{key,value:JSON值}]}]}。snapshot ID与每份state的key唯一，未知parent或任意parent环ValueError。full必须parent=null且start=0；incremental只有parent有效、parent.end==start且epoch相等才可恢复（不满足为不可恢复，不是schema错误）。valid=false的节点及其后代不可恢复；只有end<=target可选。先最大化恢复点end，再最小化整条链cost，再按路径ID列表字典序最小选一条。输出 {feasible,chain:list[id],snapshot_end:int,cost:int,state:按key排序的完整恢复点状态}；无可恢复快照时false/[]/0/0/[]。

局部验收：`python3 products/backup_graph/check_module.py`（先生成依赖及本组件输出）。

### products/journal_restore — 连续LSN与原子事务重放

输入：`inputs/journal_restore.json`；输出：`outputs/journal_restore.json`。参数以本组件 contract.json 为准。

输入 {checkpoint:int>=-1,records:[{lsn:int>=0,epoch:int>=0,tx:str,kind:write/commit/abort,...}]}。write含key:str、value:JSON值、seq:int>=0；commit含count:int>=0；abort无额外必需字段。每lsn取最高epoch，任意相同lsn/epoch内容冲突ValueError，相同内容去重；从checkpoint+1连续扫描，首缺口停止。按LSN积累每tx的writes；commit须seq恰为0..count-1，每key可重复并按seq覆盖，之后才一次输出原子事务；缺写commit标为incomplete，不输出部分写。abort丢弃事务。已扫描前缀内commit/abort后又出现同tx记录ValueError。输出 {watermark:int,transactions:[{tx,commit_lsn,writes:[{key,value}],duration:int}],incomplete:list[tx],incomplete_commits:[{tx,commit_lsn}]}；transactions和incomplete_commits按(commit_lsn,tx)，duration为write条数，writes按seq，incomplete含未结束/缺写事务并按tx排序。空records返回checkpoint及空集合。

局部验收：`python3 products/journal_restore/check_module.py`（先生成依赖及本组件输出）。

### products/backup_windows — 快照与原子日志的恢复一致性核验

输入：`inputs/backup_windows.json`, `outputs/backup_graph.json`, `outputs/journal_restore.json`；输出：`outputs/backup_windows.json`。参数以本组件 contract.json 为准。

输入顺序为 {target:int>=0,rto:int>=0,expected_sha256:64位小写hex}、recovery_chain结果、transaction_replay结果。要求snapshot可行、snapshot_end<=target、日志watermark>=target，且snapshot_end<commit_lsn<=target范围没有incomplete_commits。取该范围的原子事务按commit顺序应用到snapshot.state；不能应用仅有部分writes或aborted事务。耗时=备份链cost+所应用事务duration之和。输出 {feasible,reason:ok/snapshot/gap/transaction/rto/digest,applied:list[tx],state:[{key,value}],sha256:str,cost:int}，state按key；digest为state规范紧凑JSON的SHA256。snapshot/gap/transaction失败输出空applied/state、sha256为空、cost=0；其余失败保留计算结果。失败优先级为snapshot、gap、transaction、rto、digest，不能因目标摘要恰好一致而忽略缺写的已提交事务。

局部验收：`python3 products/backup_windows/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'备份恢复认证',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

先运行 `python3 materialize.py`；该脚本校验内嵌物化清单的 SHA-256，生成 inputs/、products/ 的契约、检查与缺失实现占位。重复执行会保留实现，只核对受保护生成文件；冲突时失败。随后检查新出现的三个产品目录并实现工具。仅在物化完成后，产品分支才可执行。

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
