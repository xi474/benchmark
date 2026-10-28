# 存储分层迁移

核验对象完整性、复制滞后和搬迁失败，平衡审核负载并计算迁移关键路径。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

## 不可修改文件

README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。

## 组件接口

契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。

- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。

- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。

- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。

context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。

## 各组件规则

### domains/objects — 修订证据完整性

输入：`inputs/objects.json`；输出：`outputs/objects.json`。参数以本组件 contract.json 为准。

输入为记录数组，每项 id:str、revision:int>=0、owner:非空str、category:prepare/copy/verify、tags:list[str]、failures:int>=0、total:int>=1、lag:int>=0、valid:bool；failures<=total。id/owner/category/tags 去首尾空白，owner/category/tags 小写，tags 去重排序。按 id 保留最大 revision；同 id 同 revision 的规范化记录冲突报 ValueError，相同记录去重。score=ceil(20*failures/total)+offset，截断到0..20。输出 {records:[{id,source,owner,category,tags,score}],count,score_total}；source=组件名，records 按(source,id)排序。空输入产生空records和零统计。
输入、规范化、版本冲突和输出 schema 与失败率证据相同；score=(valid 为真时0否则15)+failures+offset 后截断0..20。

局部验收：`python3 domains/objects/check_module.py`（先生成依赖及本组件输出）。

### domains/replication — 修订证据延迟

输入：`inputs/replication.json`；输出：`outputs/replication.json`。参数以本组件 contract.json 为准。

输入为记录数组，每项 id:str、revision:int>=0、owner:非空str、category:prepare/copy/verify、tags:list[str]、failures:int>=0、total:int>=1、lag:int>=0、valid:bool；failures<=total。id/owner/category/tags 去首尾空白，owner/category/tags 小写，tags 去重排序。按 id 保留最大 revision；同 id 同 revision 的规范化记录冲突报 ValueError，相同记录去重。score=ceil(20*failures/total)+offset，截断到0..20。输出 {records:[{id,source,owner,category,tags,score}],count,score_total}；source=组件名，records 按(source,id)排序。空输入产生空records和零统计。
输入、规范化、版本冲突和输出 schema 与失败率证据相同；score=ceil(lag/sla)+offset 后截断0..20，sla 来自契约且大于0。

局部验收：`python3 domains/replication/check_module.py`（先生成依赖及本组件输出）。

### domains/transfers — 修订证据失败率

输入：`inputs/transfers.json`；输出：`outputs/transfers.json`。参数以本组件 contract.json 为准。

输入为记录数组，每项 id:str、revision:int>=0、owner:非空str、category:prepare/copy/verify、tags:list[str]、failures:int>=0、total:int>=1、lag:int>=0、valid:bool；failures<=total。id/owner/category/tags 去首尾空白，owner/category/tags 小写，tags 去重排序。按 id 保留最大 revision；同 id 同 revision 的规范化记录冲突报 ValueError，相同记录去重。score=ceil(20*failures/total)+offset，截断到0..20。输出 {records:[{id,source,owner,category,tags,score}],count,score_total}；source=组件名，records 按(source,id)排序。空输入产生空records和零统计。

局部验收：`python3 domains/transfers/check_module.py`（先生成依赖及本组件输出）。

### views/migration_risk — 风险排名

输入：`outputs/objects.json`；输出：`outputs/migration_risk.json`。参数以本组件 contract.json 为准。

输入为证据封装对象列表，合并 result.records；以(source,id)去重，相同键记录完全一致才可合并，否则 ValueError。选 score>=threshold 的记录，按(-score,source,id)排序后保留前limit项。输出 {records,ranking:list[source+":"+id],score_total}；records 单独按(source,id)排序，空集合输出空列表与0。

局部验收：`python3 views/migration_risk/check_module.py`（先生成依赖及本组件输出）。

### views/approval_load — 负载分配

输入：`outputs/migration_risk.json`；输出：`outputs/approval_load.json`。参数以本组件 contract.json 为准。

输入为证据封装对象列表，合并去重规则同风险排名。按(-score,source,id)依次将记录分配到当前总分最低的 reviewer，总分相同取字典序最小 reviewer。输出 {records,assignments:[{id:source+":"+id,reviewer}],loads:{reviewer:总分}}；assignments 按id排序，records按(source,id)，空输入仍保留全部reviewer的零负载。

局部验收：`python3 views/approval_load/check_module.py`（先生成依赖及本组件输出）。

### views/migration_waves — 依赖波次与条件修复

输入：`outputs/replication.json`, `outputs/transfers.json`, `outputs/approval_load.json`；输出：`outputs/migration_waves.json`。参数以本组件 contract.json 为准。

输入证据合并冲突规则同风险排名。category 次序为 prepare<copy<verify；每条记录依赖所有较早类别记录，duration=1+score//5，节点id=source+":"+id。only_if_blocking 为真且没有 tags含blocking且score>=threshold 的记录时，使用空节点集合。输出 {records,blocked:false,waves,critical_path,makespan,earliest_finish}；波次与关键路径规则同 critical_path。
首输入 {nodes:[{id:非空str,duration:int>=0,deps:list[id]}]}；重复id、重复依赖、未知依赖、自依赖或环均ValueError。每波取全部当前就绪节点并按id排序，再提交整波。earliest_finish 为最长前驱finish+duration；并列前驱或终点取完整路径ID列表字典序最小者。后续输入若为分配结果，无解时输出blocked=true及空字段；有解时给同worker的job按jobid排序后添加相邻串行依赖，新增依赖造成环也报错。正常输出 {blocked:false,waves:list[list[id]],critical_path:list[id],makespan:int,earliest_finish:{id:int}}。空图所有集合空、makespan=0。

局部验收：`python3 views/migration_waves/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'存储分层迁移',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
