# API 下线管理：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`engines/notice_windows/`、`engines/support_assignment/`、`engines/retirement_order/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
不得修改README.md、任务说明、inputs/、任何contract.json、check_module.py、根check.py或integrate.py。已有受保护稳定接口保留。

## 公共函数接口与输入解释

- `model.load_payload(path: Path)`：读取UTF-8 JSON，对象或数组顶层合法；非法JSON、顶层null/布尔/数字/字符串均抛ValueError。业务字段由transform检查。
- `transform.transform(payloads: list, contract: dict)`：payloads严格按该契约inputs的顺序传入已读取的对象或数组，返回`{"name": contract["name"], "result": 算法结果对象}`。输出恰有name/result两层；本说明各operation的输出字段均属于result，不得额外嵌套一次name/result。不得修改payloads或contract。
- 输入对象仅当键集合恰好是`{"name","result"}`时视为上游组件封装；先读取其result，再使用对应operation约定的字段。原始本地对象不是文件路径，也不当成records或nodes列表。多输入operation必须消费全部指定输入，不能复制固定上游结果。
- `render.build_component(root: Path, contract_path: Path)`：读取该契约及其全部输入，调用transform并返回完整封装；执行组件render.py时写入contract.output。文件路径相对于工作区root；从任意当前目录启动均应正确，缺文件或子命令失败须失败。
- int字段严格排除bool；有限数字允许int/float但排除bool、NaN、Infinity。非空文本先检查去首尾空白后不为空；是否返回去空白/小写形式由各operation明确规定，不全局改写身份字段。列表与字典按规定类型读取，不把null当空集合，不自动把数字字符串转换成数字。
- 文中没有给出默认值的必要字段缺失、非法类型或明确列出的冲突抛ValueError；合法无解使用operation的无解结果，不等同于输入错误。词典序采用通常字符串/列表/元组顺序，相同前缀时较短列表更小。
- contract中的name/operation/inputs/output是接口字段；只有下列业务规则显式使用的算法参数参与计算，不能看到threshold便对所有operation筛选。参数值读取本组件契约，不从样例推断固定常量。

本题强化operation（notice_coverage, resource_cutover）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

## 各组件的完整业务规则

### engines/notice_windows — 带预算和期限的公告覆盖优化

operation：`notice_coverage`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {clients:[{id,weight:int>=0,deadline:int>=0,mandatory:bool}],windows:[{id,start:int>=0,end:int>start,cost:int>=0,clients:list[client_id]}],budget:int>=0,cooldown:int>=0}。重复ID/窗口内重复client/未知client、非法类型ValueError。选择互不重叠且前end+cooldown<=后start、总cost<=budget的窗口；仅end<=client.deadline的覆盖有效；同client价值只计一次。先要求覆盖所有mandatory客户，在可行集合中最大化覆盖weight之和、再最小化cost、最后取排序窗口ID列表字典序最小者。无可行集合返回feasible=false、空selected/completion、value/cost为0；成功输出 {feasible,selected,value,cost,completion:{client_id:最早有效公告end}}。空输入成功空解。实例窗口数<=16，不能用逐窗口价值相加的贪心替代集合覆盖。

补充边界：completion仅包含确实按期限覆盖的客户，不是全部客户的占位映射；对同一客户取所有选中且有效窗口的最早end。窗口即使包含过期客户仍可被选，只是该客户不计覆盖。列表平局遵循通常字典序（相同前缀时较短者优先），不额外以窗口数量为优化目标。先校验全部输入，再优化，不得借过滤掩盖非法窗口或客户。

局部检查命令：`python3 engines/notice_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### engines/support_assignment — 技能容量约束分配

operation：`capacity_assignment`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{jobs:[{id,skill:非空str,duration:int>=1}],workers:[{id,skills:list[非空str],capacity:int>=0,cost:int>=0,affinity:{job_id:int}}]}。分别检查jobs/workers的id为非空文本且去首尾空白后的id不重复；实际标识、技能匹配、输出及排序按原字符串使用，不进行大小写转换。每个job必须分配恰好一次，worker必须有完全相同的skill，且所分配duration之和<=capacity。后续输入逐个解开组件result：存在selected键时，仅保留id位于selected中的worker（selected不是job列表）；存在makespan键时，把每个剩余worker.capacity缩为min(capacity,makespan)，不是总容量。可行解依次最大化sum(worker.affinity.get(job.id,0))，最小化sum(worker.cost*job.duration)，最后按job升序形成(job,worker)元组列表并取字典序最小。result={feasible,score,cost,assignments:[{job,worker}]}，assignments按job排序。无可行分配为false/0/0/[]；没有job时为true/0/0/[]，即使worker也为空。不加入每个worker只能接一个job的限制。

局部检查命令：`python3 engines/support_assignment/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### engines/retirement_order — 有释放时间的精确资源受限调度

operation：`resource_cutover`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为本地 {nodes:[{id,client,duration:int>=1,demand:int>=1,deps:list[id]}],capacity:int>=1,horizon:int>=0}、公告notice_coverage结果、capacity_assignment结果。重复/未知/成环依赖ValueError。公告或分配不可行、任意节点client无completion或节点缺人员时，输出 {feasible:false,makespan:0,total_start:0,schedule:[]}。每节点start>=该client公告完成时间，满足所有前驱完成、同worker不可重叠、任一整数时隙sum(demand)<=capacity，end<=horizon；demand>capacity时无解。非抢占整数时刻，精确最小化makespan，再最小化sum(start)，最后按id排序后的start向量字典序取最小。输出 {feasible,makespan,total_start,schedule:[{id,start,end,worker}]}，schedule按id排序。空图可行。

补充边界：三个输入都必须参与计算，后两个输入均先解开result；本地节点id与分配结果的job对应，client与公告completion的键对应。时间区间为[start,end)，capacity是每个整数时隙的共享资源上限，不是人员总数；同worker即使总demand未超限也不能重叠。schedule中的worker来自已给分配，不在本组件重新选人。total_start只对本地节点求和；无解与上游不可行都使用同一false空schema，不返回部分方案。空图仍受上游feasible状态约束，上游均可行时输出true、makespan=total_start=0、schedule=[]。

局部检查命令：`python3 engines/retirement_order/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`API 下线管理`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
