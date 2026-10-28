# 网络策略收敛

物化工具并计算故障后的等价最短路，联合时序防火墙验证实际转发路径。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

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

### products/route_graph — 故障后的等价最短路径集

输入：`inputs/route_graph.json`；输出：`outputs/route_graph.json`。参数以本组件 contract.json 为准。

输入 {nodes:list[str],edges:[{from,to,weight:int>=1}],sources:list[id],targets:list[id],failed_nodes:list[id],failed_edges:list[[from,to]]}。节点ID/有向边唯一，端点/源/目标/故障节点或边必须存在；环合法。删除故障节点及边后，对所有source-target组合计算最短距离，并返回全部等价最短路径的第一跳。输出 {routes:[{source,target,distance:int或null,next_hops:list[id]}],active_edges:[{from,to,weight}]}，routes按(source,target)，next_hops排序，active_edges按(from,to)。source==target且未故障时distance=0、next_hops=[]；不可达distance=null。不能只保留Dijkstra的一条前驱。

局部验收：`python3 products/route_graph/check_module.py`（先生成依赖及本组件输出）。

### products/firewall_policy — 时序连接状态与双向防火墙

输入：`inputs/firewall_policy.json`；输出：`outputs/firewall_policy.json`。参数以本组件 contract.json 为准。

输入 {timeout:int>=1,rules:[{id,src:glob,dst:glob,protocol:tcp/udp/*,priority:int,effect:allow/deny}],events:[{id,ts:int>=0,seq:int>=0,src,dst,sport:int1..65535,dport:int1..65535,protocol:tcp/udp,flag:syn/data/fin/rst}]}。rule/event ID唯一，按(ts,seq,id)处理。会话用双向五元组标识；ts>=last_activity+timeout时失效。不存在会话时仅syn能开连接，按priority降序、src+dst+protocol非*?[]字符数降序、deny优先、id升序匹配规则，默认deny。存在有效会话则双向data/fin/rst或syn允许，更新last_activity；fin/rst后关闭。无会话的data/fin/rst拒绝。输出 {decisions:[{id,allowed:bool,reason:rule/state/no_session/default,rule_id:str或null,src,dst}],active_sessions:int}，decision按处理顺序；结束时active_sessions以最后事件时间清理超时。

局部验收：`python3 products/firewall_policy/check_module.py`（先生成依赖及本组件输出）。

### products/network_traces — ECMP实际路径与状态决策联合核验

输入：`inputs/network_traces.json`, `outputs/route_graph.json`, `outputs/firewall_policy.json`；输出：`outputs/network_traces.json`。参数以本组件 contract.json 为准。

输入顺序为 {probes:[{id,event,source,target,hops:list[id]}]}、ecmp_routes结果、stateful_acl结果，probe ID唯一、未知event ValueError。依次检查ACL decision.allowed及src/dst匹配（失败reason=acl），route存在且distance非null（route），hops首尾等于source/target且每条有向边在active_edges中（path），边权和等于最短distance且第一跳在next_hops内（非零路径；失败reason=non_shortest）。输出 {results:[{id,reachable:bool,reason:ok/acl/route/path/non_shortest}],reachable_count}，结果保留probe顺序。不能只相信静态可达或只看ACL放行。

局部验收：`python3 products/network_traces/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'网络策略收敛',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

先运行 `python3 materialize.py`；该脚本校验内嵌物化清单的 SHA-256，生成 inputs/、products/ 的契约、检查与缺失实现占位。重复执行会保留实现，只核对受保护生成文件；冲突时失败。随后检查新出现的三个产品目录并实现工具。仅在物化完成后，产品分支才可执行。

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
