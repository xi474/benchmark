# 搜索索引重建：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`mapping_compat/`、`shard_replay/`、`cutover_plan/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
不得修改README.md、任务说明、inputs/、任何contract.json、check_module.py、根check.py或integrate.py。已有受保护稳定接口保留。

本题各包已有__init__.py与parser.py为稳定接口，不得修改。调用`<package>.parser.parse(payloads, contract)`必须得到与该包transform相同的完整封装；同时保留可直接导入model/transform/render的函数接口。

## 公共函数接口与输入解释

- `model.load_payload(path: Path)`：读取UTF-8 JSON，对象或数组顶层合法；非法JSON、顶层null/布尔/数字/字符串均抛ValueError。业务字段由transform检查。
- `transform.transform(payloads: list, contract: dict)`：payloads严格按该契约inputs的顺序传入已读取的对象或数组，返回`{"name": contract["name"], "result": 算法结果对象}`。输出恰有name/result两层；本说明各operation的输出字段均属于result，不得额外嵌套一次name/result。不得修改payloads或contract。
- 输入对象仅当键集合恰好是`{"name","result"}`时视为上游组件封装；先读取其result，再使用对应operation约定的字段。原始本地对象不是文件路径，也不当成records或nodes列表。多输入operation必须消费全部指定输入，不能复制固定上游结果。
- `render.build_component(root: Path, contract_path: Path)`：读取该契约及其全部输入，调用transform并返回完整封装；执行组件render.py时写入contract.output。文件路径相对于工作区root；从任意当前目录启动均应正确，缺文件或子命令失败须失败。
- int字段严格排除bool；有限数字允许int/float但排除bool、NaN、Infinity。非空文本先检查去首尾空白后不为空；是否返回去空白/小写形式由各operation明确规定，不全局改写身份字段。列表与字典按规定类型读取，不把null当空集合，不自动把数字字符串转换成数字。
- 文中没有给出默认值的必要字段缺失、非法类型或明确列出的冲突抛ValueError；合法无解使用operation的无解结果，不等同于输入错误。词典序采用通常字符串/列表/元组顺序，相同前缀时较短列表更小。
- contract中的name/operation/inputs/output是接口字段；只有下列业务规则显式使用的算法参数参与计算，不能看到threshold便对所有operation筛选。参数值读取本组件契约，不从样例推断固定常量。

本题强化operation（quorum_cutover, schema_migration, shard_replay）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

### 模式比较的完整共用定义

首输入{old:[{name,type,required,default?}],new:[同格式]}。name去空白且非空，每个数组内规范化name唯一；type只能int/float/str/bool，required必须是布尔。default只看字段是否存在，不以truthiness判断，也不要求自动类型转换。按字段名并集升序输出changes：删除旧字段→{field,code:removed,breaking:true}；新增字段→code:added，仅required=true且没有default键时breaking=true；同名类型改变→code:type，只有int→float为非breaking；旧required=false变新true→再追加code:required，仅新字段没有default键时breaking=true。类型与required同时改变时，同一字段先type后required；required=true变false不单独产生change，单独default变化也不产生change。result={compatible:没有任何breaking change,changes}。空old/new为true和[]；不返回records或组件依赖图。

## 各组件的完整业务规则

### mapping_compat — 重命名图解析与模式迁移

operation：`schema_migration`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {old:list[field],new:list[field],renames:[{from:str,to:str}]}，field同schema_compatibility。from唯一，重命名形成有向图，链式解析至最终名字，任何环（包括未被old字段使用的环）ValueError；不同old字段归一至同终点ValueError。将old字段重命名后，按schema_compatibility规则判断删除、增加、int->float拓宽、required/default；输出 {compatible,changes,field_map:{old_name:terminal_name}}。field_map按原字段名，changes排序同原算法；空输入可行。

补充边界：先检查全部renames的环，包括未由old字段到达的分量。from和to去空白；重复from即使指向相同to也报错。field_map对每个old字段给出最终名称，未参与重命名者映射到自身；终点未出现在new时按removed处理，并不因此免除删除破坏性。changes.field使用重命名后的字段名；类型与required的同字段change顺序、default存在性按本说明的模式规则，不增加rename这一change code。

局部检查命令：`python3 mapping_compat/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### shard_replay — 分片日志缺口与墓碑恢复

operation：`shard_replay`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {replicas:[{id,shard,host,checkpoint:int>=-1,documents:[{id,version:int>=0,fields:dict}]}],events:[{replica,offset:int>=0,epoch:int>=0,op:upsert/delete,id,version:int>=0,fields:dict(仅upsert)}]}。replica ID和初始document ID分别唯一，未知replica ValueError。相同(replica,offset)取最高epoch；任意同epoch不同内容冲突ValueError，相同内容重复允许。从checkpoint+1逐个处理连续offset，首个缺口停止。每document只接受更高version；相同version相同内容幂等、不同内容（包括delete与upsert）冲突；较低version忽略，墓碑保留版本防止旧upsert复活。输出 {replicas:[{id,shard,host,applied_offset,documents:[{id,version,fields}],tombstones:{id:version},sha256}]}，副本与documents按id，摘要对documents的UTF-8紧凑sort_keys JSON计算SHA256；空副本表返回空列表。

补充边界：先检查所有事件版本的offset冲突，包括checkpoint之前和缺口之后的事件；同一事件版本比较整条事件对象。只有连续前缀实际执行document版本冲突检查。delete留下(id,version)墓碑，文档列表不输出墓碑；同version的delete/delete幂等，upsert/upsert仅fields相同才幂等，二者相遇冲突。applied_offset为空连续前缀时保留checkpoint。摘要只覆盖最终documents列表，不包括tombstones、host、shard或整个副本对象。fields是对象，空对象合法；本operation不在最终文档上额外套用schema_migration。

局部检查命令：`python3 shard_replay/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### cutover_plan — 副本仲裁与预算最优切换

operation：`quorum_cutover`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为 {partitions:[{id,quorum:int>=1,value:int>=0,target_sha256:str,target_offset:int>=-1}],candidates:[{id,replica,cost:int>=0}],budget:int>=0}、schema_migration结果、shard_replay结果。各数组ID唯一；未知replica或分片、同replica多个candidate、非法digest ValueError。只有摘要等于对应partition.target_sha256且applied_offset>=target_offset的副本候选可用。选择总cost<=budget的候选集合；同partition同host最多一个、每partition所选数只能为0或恰好quorum。最大化已满足partition.value总和，再最小cost，再排序candidate ID列表字典序最小。模式不兼容返回blocked=true及空选择；否则输出 {blocked:false,selected,partitions:已满足分片ID排序,value,cost}。<=14候选，需精确优化，不能逐副本贪心或用副本数量替代独立host仲裁。

补充边界：每个分片允许完全不选择；选了则必须恰好quorum个不同host，不能用“至少quorum”替代。value按成功切换的partition计一次，不按副本累加；同host限制作用于同一partition，不跨partition排斥host。模式不兼容时返回blocked=true、selected/partitions=[]、value=cost=0；模式兼容但没有合格候选时仍是blocked=false的空解。先验证候选/副本/分片引用和digest，不能因为schema不兼容就跳过输入校验。selected是candidate id，不是replica id。

局部检查命令：`python3 cutover_plan/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`搜索索引重建`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
