# 租户配额再平衡：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`engines/rebalance_windows/`、`engines/resource_order/`、`engines/operator_assignment/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
不得修改README.md、任务说明、inputs/、任何contract.json、check_module.py、根check.py或integrate.py。已有受保护稳定接口保留。

## 公共函数接口与输入解释

- `model.load_payload(path: Path)`：读取UTF-8 JSON，对象或数组顶层合法；非法JSON、顶层null/布尔/数字/字符串均抛ValueError。业务字段由transform检查。
- `transform.transform(payloads: list, contract: dict)`：payloads严格按该契约inputs的顺序传入已读取的对象或数组，返回`{"name": contract["name"], "result": 算法结果对象}`。输出恰有name/result两层；本说明各operation的输出字段均属于result，不得额外嵌套一次name/result。不得修改payloads或contract。
- 输入对象仅当键集合恰好是`{"name","result"}`时视为上游组件封装；先读取其result，再使用对应operation约定的字段。原始本地对象不是文件路径，也不当成records或nodes列表。多输入operation必须消费全部指定输入，不能复制固定上游结果。
- `render.build_component(root: Path, contract_path: Path)`：读取该契约及其全部输入，调用transform并返回完整封装；执行组件render.py时写入contract.output。文件路径相对于工作区root；从任意当前目录启动均应正确，缺文件或子命令失败须失败。
- int字段严格排除bool；有限数字允许int/float但排除bool、NaN、Infinity。非空文本先检查去首尾空白后不为空；是否返回去空白/小写形式由各operation明确规定，不全局改写身份字段。列表与字典按规定类型读取，不把null当空集合，不自动把数字字符串转换成数字。
- 文中没有给出默认值的必要字段缺失、非法类型或明确列出的冲突抛ValueError；合法无解使用operation的无解结果，不等同于输入错误。词典序采用通常字符串/列表/元组顺序，相同前缀时较短列表更小。
- contract中的name/operation/inputs/output是接口字段；只有下列业务规则显式使用的算法参数参与计算，不能看到threshold便对所有operation筛选。参数值读取本组件契约，不从样例推断固定常量。

## 各组件的完整业务规则

### engines/rebalance_windows — 带冷却期的加权区间选择

operation：`weighted_intervals`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入首对象{windows:[{id:非空str,start:int>=0,end:int>start,value:int}]}，契约cooldown:int>=0。id去首尾空白后唯一；重复id即ValueError。半开区间相容条件为较早窗口end+cooldown<=较晚窗口start。输出result={selected:[排序后的规范化id],value:所选value之和}。优化顺序：总value最大；再比较排序后的整个ID列表，按通常字典序取最小，较短的相同前缀列表更小。允许负value和0值，允许空集合；若最优价值为0，空列表优于所有非空同价值列表。不得只给DP局部状态按单个ID打破平局，也不能仅因窗口value为0就一概排除它——它可能改变正价值最优解的完整ID列表平局。空windows为selected=[]、value=0。本operation只消费首输入，契约threshold不参与目标。

局部检查命令：`python3 engines/rebalance_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### engines/resource_order — 依赖图与确定性关键路径

operation：`critical_path`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{nodes:[{id:非空str,duration:int>=0,deps:list[id]}]}。节点id去首尾空白后唯一，节点输出id为去空白值；依赖引用必须准确匹配这些id。重复id/依赖、未知依赖、自依赖和环均ValueError。后续组件result若有feasible字段：false直接返回{blocked:true,waves:[],critical_path:[],makespan:0,earliest_finish:{}}；true则读取assignments中的job/worker，同一worker的job按jobid升序，相邻job添加先后依赖。新增边也必须无环；未知被分配job报错；未分配节点仍按原依赖存在。没有分配结果时绝不凭空添加人员依赖。每波取本波开始时全部就绪节点并按id排序；finish=duration+最大前驱finish。最大finish的前驱并列时，比较前驱已经形成的完整路径（不含当前节点）取字典序最小，然后追加当前节点；最后在最大finish终点间按其完整路径列表取最小。正常result={blocked:false,waves,critical_path,makespan,earliest_finish}，earliest_finish按id；空图的两个列表与映射为空、makespan=0。不要把分配结果封装的name/result两层误当作assignments。

局部检查命令：`python3 engines/resource_order/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### engines/operator_assignment — 技能容量约束分配

operation：`capacity_assignment`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{jobs:[{id,skill:非空str,duration:int>=1}],workers:[{id,skills:list[非空str],capacity:int>=0,cost:int>=0,affinity:{job_id:int}}]}。分别检查jobs/workers的id为非空文本且去首尾空白后的id不重复；实际标识、技能匹配、输出及排序按原字符串使用，不进行大小写转换。每个job必须分配恰好一次，worker必须有完全相同的skill，且所分配duration之和<=capacity。后续输入逐个解开组件result：存在selected键时，仅保留id位于selected中的worker（selected不是job列表）；存在makespan键时，把每个剩余worker.capacity缩为min(capacity,makespan)，不是总容量。可行解依次最大化sum(worker.affinity.get(job.id,0))，最小化sum(worker.cost*job.duration)，最后按job升序形成(job,worker)元组列表并取字典序最小。result={feasible,score,cost,assignments:[{job,worker}]}，assignments按job排序。无可行分配为false/0/0/[]；没有job时为true/0/0/[]，即使worker也为空。不加入每个worker只能接一个job的限制。

局部检查命令：`python3 engines/operator_assignment/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`租户配额再平衡`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
