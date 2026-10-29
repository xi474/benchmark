# 存储分层迁移工具

修复一个接口已约定、实现缺失的本地 Python 仓库。系统核验存储对象、复制延迟和搬迁失败证据，生成风险排名、审核负载及迁移分析报告。只使用 Python 标准库，所有结果必须从输入计算。

## 实现与保护范围

- 实现六个组件目录中的 model.py、transform.py、render.py，以及根 run_all.py、final_report.py。可添加私有辅助模块。
- 不得修改本说明、任务文本、inputs/、任何 contract.json、check_module.py、根 check.py 或 integrate.py。不要将作者参考实现、外部 verifier 或历史产物复制进工作区。
- 必需文件接口由现有契约给定。执行方式与可执行条件由实际读取到的信息确定；文件名排序不代表合法执行顺序。

## 公共接口与序列化

所有组件使用相同接口。契约 JSON 字段的排列顺序不影响语义。

|接口|行为|
|---|---|
|`model.load_payload(path: Path)`|读取 JSON 对象或数组。非法 JSON、其他顶层类型抛 ValueError。业务字段验证由 transform 完成。|
|`transform.transform(payloads: list, contract: dict)`|按 inputs 顺序接收已加载内容，返回 `{"name": contract["name"], "result": 业务结果}`，不修改 payloads 或 contract。|
|`render.build_component(root: Path, contract_path: Path)`|读取契约及其全部输入，调用 transform，返回完整封装对象。|
|`python3 <组件目录>/render.py`|将完整封装对象写入契约 output。从任意当前目录启动均应正确定位工作区；缺失必需输入必须报错。|

下文的输出字段均指封装内的 result，不再额外嵌套封装。JSON 使用 UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾恰有一个换行。

整数使用真正的 JSON 整数，bool 不得当成整数；必需字段缺失、非法类型和规定的冲突以 ValueError 报错。不得修改传入对象，不得把失败改写为成功的空结果。

## 证据组件

|目录|输入|输出|operation|
|---|---|---|---|
|domains/objects|inputs/objects.json|outputs/objects.json|integrity_evidence|
|domains/replication|inputs/replication.json|outputs/replication.json|lag_evidence|
|domains/transfers|inputs/transfers.json|outputs/transfers.json|failure_evidence|

### 输入与版本选择

输入为记录数组，每条记录具有：

- id：去首尾空白后的非空字符串，保留大小写。
- revision：整数且不小于0。
- owner：非空字符串，去首尾空白并转小写。
- category：去首尾空白并转小写后属于 prepare、copy、verify。
- tags：字符串数组；各值去首尾空白、转小写，不能变成空串，最终去重排序。
- failures：整数且不小于0；total：整数且不小于1；failures<=total。
- lag：整数且不小于0；valid：布尔值。

先验证并规范化全部记录。相同 (id,revision) 的上述规范化字段必须完全一致，否则报错；一致的重复记录合并。再按 id 保留最大 revision 的记录。非最大 revision 的冲突也不能忽略。额外未使用字段不参与规范化记录的版本冲突比较。

### 评分与输出

offset、sla 等参数取自对应契约，sla 为正数。三种公式各自独立适用：

|组件|基础分|最终分|
|---|---|---|
|objects|`(0 if valid else 15) + failures`|基础分加 offset，限制到闭区间 [0,20]|
|replication|`ceil(lag / sla)`|基础分加 offset，限制到闭区间 [0,20]|
|transfers|`ceil(20 * failures / total)`|基础分加 offset，限制到闭区间 [0,20]|

证据组件不根据 threshold 丢弃低分记录。

结果为 `{records,count,score_total}`。每条输出记录只含 `{id,source,owner,category,tags,score}`，source=contract["name"]；records 按 (source,id) 排序，count 为保留记录数，score_total 为这些记录的 score 总和。空输入返回空 records，两个统计值均为0。

局部检查：`python3 domains/<组件名>/check_module.py`，使用真实输入与输出，执行前相关文件必须存在。

## 视图组件

|目录|契约中的必需输入|输出|
|---|---|---|
|views/migration_risk|outputs/objects.json|outputs/migration_risk.json|
|views/approval_load|outputs/migration_risk.json|outputs/approval_load.json|
|views/migration_waves|outputs/replication.json、outputs/transfers.json、outputs/approval_load.json|outputs/migration_waves.json|

### 共用记录合并规则

从每个输入封装的 result.records 取记录，按完整 (source,id) 去重。同键记录完全相同才可合并，否则抛 ValueError。不得去掉 source、截取 id 后缀、修改来源或将不同 source 的记录视为同一条。合并不改变输入对象。

### migration_risk：三个字段基于同一个筛选集合

R 为全部合并记录。S 为 R 中 score>=threshold 的记录，按 (-score,source,id) 排序后保留前 limit 条；threshold、limit 来自契约。

返回 `{records,ranking,score_total}`，三者都只基于 S：

- records：S 的完整记录，改按 (source,id) 排序；不得返回全部 R。
- ranking：S 保持风险排名顺序，逐条生成完整字符串 source+":"+id。
- score_total：S 中 score 的总和，不是全部输入的总和。

两种排序分别用于不同字段。即使输入非空，只要 S 为空，也返回 records=[]、ranking=[]、score_total=0。

### approval_load：分配全部传入记录

合并输入后按 (-score,source,id) 遍历。契约 reviewers 中每个 reviewer 的初始累计分数为0。每次选当前累计分数最低者，同分取 reviewer 字符串字典序最小者；分配后加上该记录 score。

返回 `{records,assignments,loads}`：

- records：全部合并输入记录，按 (source,id) 排序；不再次应用 threshold 或 limit。
- assignments：每条记录恰好一个 `{id:source+":"+id,reviewer}`，最终按完整 id 排序。
- loads：包含全部 reviewer 及累计分数，保留零负载 reviewer。

空输入时 records、assignments 为空，loads 仍保留全部 reviewer 的零值。本组件不返回 feasible、job 或 worker 字段。

### migration_waves：合并 records，计算业务图

输入均为上表中的组件封装，不是 `{nodes:...}`。合并所有输入的 result.records，包括 approval_load 的 records；不能只合并前两个证据文件。

本组件不消费 assignments 或 loads，不根据 reviewer 增加边，不匹配 job/worker，也不推断分配无解；approval_load 输入被使用的是它的 records。

only_if_blocking 只决定用于构图的记录集合：

- false：保留全部合并记录，不按 threshold 逐条筛选。
- true 且存在 tags 含 blocking、score>=threshold 的记录：仍保留全部合并记录。
- true 但不存在上述记录：使用空记录集合及空图；不表示 blocked=true。

对选定集合中每条记录构建一个业务节点：id=source+":"+id，duration=1+score//5。类别次序 prepare<copy<verify；节点前驱为集合中所有类别严格更早的节点，同类别不增加边。

返回 `{records,blocked,waves,critical_path,makespan,earliest_finish}`：

- records：最终用于构图的集合，按 (source,id) 排序。
- blocked：本组件的合法输入结果恒为 false。
- waves：每轮取全部尚未处理、前驱均已处理的节点，按完整 id 排序形成列表，再提交该整轮，得到列表的列表。
- earliest_finish[id]：无前驱时为 duration，否则为最大前驱 earliest_finish 加本节点 duration。
- critical_path：总 duration 最大的路径 ID 列表；同最大时长取完整路径 ID 列表字典序最小者。
- makespan：最大 earliest_finish。

空集合返回 records、waves、critical_path 为空列表，earliest_finish 为空对象，makespan=0、blocked=false。此业务图是要计算的输出语义，不指定 Agent 拆分方式。

视图局部检查：`python3 views/<组件名>/check_module.py`，使用真实文件，不得伪造输入或输出绕过检查。

## 根入口与最终报告

run_all.py 必须从任意当前目录定位工作区，根据真实文件接口完成全部必要计算、调用已有集成命令并生成最终报告。不得复用旧 outputs 掩盖错误执行条件，不得用假空文件代替必需输入；任何子进程失败必须传播非零退出码。

integrate.py 已提供，不修改。根模式读取六个组件产物，写 outputs/core_manifest.json，格式为 `{"components":{组件名:result}}`。其另外支持的 domains 模式不是本任务必需接口，不能凭模式名引入额外产物或规则。

final_report.py 读取完整 core_manifest 对象，写 outputs/final_report.json：

- title："存储分层迁移"。
- component_count：core_object["components"] 的条目数。
- sha256：完整 core_object 的规范化 JSON 字节摘要，保留最外层 components 键。
- attention：各组件 result 中，blocked 为真、feasible/compatible 显式为假、deny>0 或 score_total>=20 任一条件成立的组件名，去重并按名字排序；缺失字段不触发条件。

摘要对象与编码明确为：

```text
core_object = json.loads(core_manifest 文件内容)
digest_input = json.dumps(core_object, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
sha256 = SHA256(digest_input).hexdigest()
```

不能仅对 core_object["components"] 求摘要；不能直接对文件原始字节求摘要，也不把文件末尾换行加进 digest_input。

## 验收

运行 `python3 check.py`。它会清理 outputs，执行根入口、检查文件结构并运行全部局部检查，因此根入口必须能从干净状态重建产物。

可见检查主要检验可运行性与文件/函数结果的一致性，不能等同于独立业务正确性证明。正式评分在工作区外校验受保护文件、完整业务产物、规范化 JSON 与未见输入接口行为。不得修改检查、读取隐藏参考答案或硬编码旧输出。
