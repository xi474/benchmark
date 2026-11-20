# 网络策略收敛：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`products/route_graph/`、`products/firewall_policy/`、`products/network_traces/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

本题强化operation（ecmp_routes, network_join, stateful_acl）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

## 各组件的完整业务规则

### products/route_graph — 故障后的等价最短路径集

operation：`ecmp_routes`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {nodes:list[str],edges:[{from,to,weight:int>=1}],sources:list[id],targets:list[id],failed_nodes:list[id],failed_edges:list[[from,to]]}。节点ID/有向边唯一，端点/源/目标/故障节点或边必须存在；环合法。删除故障节点及边后，对所有source-target组合计算最短距离，并返回全部等价最短路径的第一跳。输出 {routes:[{source,target,distance:int或null,next_hops:list[id]}],active_edges:[{from,to,weight}]}，routes按(source,target)，next_hops排序，active_edges按(from,to)。source==target且未故障时distance=0、next_hops=[]；不可达distance=null。不能只保留Dijkstra的一条前驱。

补充边界：sources、targets、failed_nodes和failed_edges的重复引用按集合处理，nodes重复和有向边重复则错误。失效节点仍可作为被请求的source/target，此时对应route不可达；不从routes里删除该组合。active_edges返回全部存活原边，不只是最短路树。next_hops只列满足distance(source)=weight(source,hop)+distance(hop)的直接后继，不是整条路径或全部可达邻居。源目标相同且存活时为0和[]，缺失路径distance=null且next_hops=[]。

局部检查命令：`python3 products/route_graph/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/firewall_policy — 时序连接状态与双向防火墙

operation：`stateful_acl`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {timeout:int>=1,rules:[{id,src:glob,dst:glob,protocol:tcp/udp/*,priority:int,effect:allow/deny}],events:[{id,ts:int>=0,seq:int>=0,src,dst,sport:int1..65535,dport:int1..65535,protocol:tcp/udp,flag:syn/data/fin/rst}]}。rule/event ID唯一，按(ts,seq,id)处理。会话用双向五元组标识；ts>=last_activity+timeout时失效。不存在会话时仅syn能开连接，按priority降序、src+dst+protocol非*?[]字符数降序、deny优先、id升序匹配规则，默认deny。存在有效会话则双向data/fin/rst或syn允许，更新last_activity；fin/rst后关闭。无会话的data/fin/rst拒绝。输出 {decisions:[{id,allowed:bool,reason:rule/state/no_session/default,rule_id:str或null,src,dst}],active_sessions:int}，decision按处理顺序；结束时active_sessions以最后事件时间清理超时。

补充边界：会话键为(protocol,排序后的两个端点(src,sport)/(dst,dport))，使反向报文匹配同一会话；不同端口或协议不是同一会话。在处理每条事件之前，先以该事件时间清理全部超时会话，最后返回的active_sessions即最后一条事件处理后的状态。无session且非syn的拒绝优先于静态规则；已有session不重新跑规则，即使其方向匹配deny。state/no_session/default的rule_id=null，reason=rule时才返回胜出规则id，包括rule拒绝。不按TCP/UDP自行引入未声明的额外状态机。

局部检查命令：`python3 products/firewall_policy/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/network_traces — ECMP实际路径与状态决策联合核验

operation：`network_join`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为 {probes:[{id,event,source,target,hops:list[id]}]}、ecmp_routes结果、stateful_acl结果，probe ID唯一、未知event ValueError。依次检查ACL decision.allowed及src/dst匹配（失败reason=acl），route存在且distance非null（route），hops首尾等于source/target且每条有向边在active_edges中（path），边权和等于最短distance且第一跳在next_hops内（非零路径；失败reason=non_shortest）。输出 {results:[{id,reachable:bool,reason:ok/acl/route/path/non_shortest}],reachable_count}，结果保留probe顺序。不能只相信静态可达或只看ACL放行。

补充边界：所有探针都按本地顺序输出，ACL结果根据event的id查找；未知event属于ValueError而非reachable=false。按acl→route→path→non_shortest→ok的优先级选择reason，不能因一个后续条件失败覆盖更早的失败。非零路径至少两节点且首跳需在next_hops，零距离允许[source]且边权和为0；不能强制零距离也有首跳。route/ACL均须实际来自两个上游结果，不能从本地缓存或静态规则推定。

局部检查命令：`python3 products/network_traces/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`网络策略收敛`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
