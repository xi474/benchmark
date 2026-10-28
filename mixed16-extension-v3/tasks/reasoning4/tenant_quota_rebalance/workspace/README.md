# 租户配额再平衡

先确定配额调整窗口与资源依赖，再在窗口和容量双约束下分配执行人员。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

## 不可修改文件

README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。

## 组件接口

契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。

- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。

- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。

- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。

context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。

## 各组件规则

### engines/rebalance_windows — 带冷却期的加权区间选择

输入：`inputs/rebalance_windows.json`；输出：`outputs/rebalance_windows.json`。参数以本组件 contract.json 为准。

输入 {windows:[{id:非空str,start:int>=0,end:int>start,value:int}]}，清理后重复id报ValueError。窗口为半开区间，前一end+cooldown<=后一start才相容。最大化总value，允许选空集合和负value；平局选排序后ID元组字典序最小者。输出 {selected:按id排序列表,value:总价值}，空输入为[]和0。推荐动态规划，不能按价值贪心。

局部验收：`python3 engines/rebalance_windows/check_module.py`（先生成依赖及本组件输出）。

### engines/resource_order — 依赖图与确定性关键路径

输入：`inputs/resource_order.json`；输出：`outputs/resource_order.json`。参数以本组件 contract.json 为准。

首输入 {nodes:[{id:非空str,duration:int>=0,deps:list[id]}]}；重复id、重复依赖、未知依赖、自依赖或环均ValueError。每波取全部当前就绪节点并按id排序，再提交整波。earliest_finish 为最长前驱finish+duration；并列前驱或终点取完整路径ID列表字典序最小者。后续输入若为分配结果，无解时输出blocked=true及空字段；有解时给同worker的job按jobid排序后添加相邻串行依赖，新增依赖造成环也报错。正常输出 {blocked:false,waves:list[list[id]],critical_path:list[id],makespan:int,earliest_finish:{id:int}}。空图所有集合空、makespan=0。

局部验收：`python3 engines/resource_order/check_module.py`（先生成依赖及本组件输出）。

### engines/operator_assignment — 技能容量约束分配

输入：`inputs/operator_assignment.json`, `outputs/rebalance_windows.json`, `outputs/resource_order.json`；输出：`outputs/operator_assignment.json`。参数以本组件 contract.json 为准。

首输入 {jobs:[{id,skill:str,duration:int>=1}],workers:[{id,skills:list[str],capacity:int>=0,cost:int>=0,affinity:{jobid:int}}]}。各数组清理后ID不得重复；ID和技能按输入有效非空文本使用。全部job必须分配到具备skill且累计duration不超过capacity的worker；先最大化affinity总和，再最小化sum(cost*duration)，最后按排序后的(job,worker)元组序打破平局。后续输入若有selected，仅保留这些worker；若有makespan，每worker容量再截断到makespan。输出 {feasible,score,cost,assignments:[{job,worker}]}，assignments按job排序。无解时false/0/0/[]；无job时true/0/0/[]。

局部验收：`python3 engines/operator_assignment/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'租户配额再平衡',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
