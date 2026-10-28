# API 下线管理

优化带预算和期限的公告覆盖，并联合人员分配精确求解资源受限下线调度。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

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

### engines/notice_windows — 带预算和期限的公告覆盖优化

输入：`inputs/notice_windows.json`；输出：`outputs/notice_windows.json`。参数以本组件 contract.json 为准。

输入 {clients:[{id,weight:int>=0,deadline:int>=0,mandatory:bool}],windows:[{id,start:int>=0,end:int>start,cost:int>=0,clients:list[client_id]}],budget:int>=0,cooldown:int>=0}。重复ID/窗口内重复client/未知client、非法类型ValueError。选择互不重叠且前end+cooldown<=后start、总cost<=budget的窗口；仅end<=client.deadline的覆盖有效；同client价值只计一次。先要求覆盖所有mandatory客户，在可行集合中最大化覆盖weight之和、再最小化cost、最后取排序窗口ID列表字典序最小者。无可行集合返回feasible=false、空selected/completion、value/cost为0；成功输出 {feasible,selected,value,cost,completion:{client_id:最早有效公告end}}。空输入成功空解。实例窗口数<=16，不能用逐窗口价值相加的贪心替代集合覆盖。

局部验收：`python3 engines/notice_windows/check_module.py`（先生成依赖及本组件输出）。

### engines/support_assignment — 技能容量约束分配

输入：`inputs/support_assignment.json`；输出：`outputs/support_assignment.json`。参数以本组件 contract.json 为准。

首输入 {jobs:[{id,skill:str,duration:int>=1}],workers:[{id,skills:list[str],capacity:int>=0,cost:int>=0,affinity:{jobid:int}}]}。各数组清理后ID不得重复；ID和技能按输入有效非空文本使用。全部job必须分配到具备skill且累计duration不超过capacity的worker；先最大化affinity总和，再最小化sum(cost*duration)，最后按排序后的(job,worker)元组序打破平局。后续输入若有selected，仅保留这些worker；若有makespan，每worker容量再截断到makespan。输出 {feasible,score,cost,assignments:[{job,worker}]}，assignments按job排序。无解时false/0/0/[]；无job时true/0/0/[]。

局部验收：`python3 engines/support_assignment/check_module.py`（先生成依赖及本组件输出）。

### engines/retirement_order — 有释放时间的精确资源受限调度

输入：`inputs/retirement_order.json`, `outputs/notice_windows.json`, `outputs/support_assignment.json`；输出：`outputs/retirement_order.json`。参数以本组件 contract.json 为准。

输入顺序为本地 {nodes:[{id,client,duration:int>=1,demand:int>=1,deps:list[id]}],capacity:int>=1,horizon:int>=0}、公告notice_coverage结果、capacity_assignment结果。重复/未知/成环依赖ValueError。公告或分配不可行、任意节点client无completion或节点缺人员时，输出 {feasible:false,makespan:0,total_start:0,schedule:[]}。每节点start>=该client公告完成时间，满足所有前驱完成、同worker不可重叠、任一整数时隙sum(demand)<=capacity，end<=horizon；demand>capacity时无解。非抢占整数时刻，精确最小化makespan，再最小化sum(start)，最后按id排序后的start向量字典序取最小。输出 {feasible,makespan,total_start,schedule:[{id,start,end,worker}]}，schedule按id排序。空图可行。<=7节点，可用枚举拓扑优先序的串行最早可行插入生成器，不能仅计算无限资源关键路径。

局部验收：`python3 engines/retirement_order/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'API 下线管理',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
