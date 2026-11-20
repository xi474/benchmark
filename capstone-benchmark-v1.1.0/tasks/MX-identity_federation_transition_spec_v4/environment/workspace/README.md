# 身份联邦迁移：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`claims/`、`sessions/`、`authorization/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

本题强化operation（federation_authorize, session_replay）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

## 各组件的完整业务规则

### claims — 字段模式兼容

operation：`schema_compatibility`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{old:[{name,type,required,default?}],new:[同格式]}。name去空白且非空，每个数组内规范化name唯一；type只能int/float/str/bool，required必须是布尔。default只看字段是否存在，不以truthiness判断，也不要求自动类型转换。按字段名并集升序输出changes：删除旧字段→{field,code:removed,breaking:true}；新增字段→code:added，仅required=true且没有default键时breaking=true；同名类型改变→code:type，只有int→float为非breaking；旧required=false变新true→再追加code:required，仅新字段没有default键时breaking=true。类型与required同时改变时，同一字段先type后required；required=true变false不单独产生change，单独default变化也不产生change。result={compatible:没有任何breaking change,changes}。空old/new为true和[]；不返回records或组件依赖图。

局部检查命令：`python3 claims/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### sessions — 乱序令牌轮换及传递撤销

operation：`session_replay`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {now:int>=0,events:[{id,ts:int>=0,kind:issue/refresh/revoke,token:str,...}]}，event ID唯一，按(ts,kind优先级revoke<issue<refresh,id)处理，ts>now的事件不执行但仍校验schema。issue含subject非空str、expires:int>ts、groups:list[str]；refresh含parent:str、expires:int>ts；revoke不带额外必需字段。token只能issue/refresh一次，否则ValueError。revoke可先于签发，撤销标记永久保留；刷新父令牌必须已签发、在刷新时未到期且其祖先未撤销，否则子令牌被签发但永久无效。有效refresh继承subject/groups，轮换后父令牌标为superseded且不能再次刷新；祖先之后撤销也使全部后代无效，但祖先自然到期或被轮换不使已签发子令牌失效。输出 {active_tokens:[{token,subject,groups,expires}],invalid_tokens:list[token],revoked:list[token]}；now>=expires失效，各列表按token排序，groups去重排序。缺字段、非法类型ValueError。

补充边界：校验阶段覆盖全部事件，包括未来事件，且issue/refresh的token唯一性也跨未来事件检查；未来事件不进入输出状态。撤销可针对从未签发的token，revoked仍保留该标识。只有有效refresh才将父token置superseded；无效子token仍出现在invalid_tokens，但不消耗父token的轮换机会。祖先自然过期与superseded不追溯影响已有效签发的子token；永久撤销才沿祖先链传播。三类token列表指已处理事件得到的状态，invalid_tokens不包含纯未来签发。subject/token/group身份保持原值，不统一小写。

局部检查命令：`python3 sessions/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### authorization — 组继承闭包与跨组件授权

operation：`federation_authorize`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为 {groups:[{id,parents:list[group_id],roles:list[str]}],rules:[{id,role,resource:glob,action:glob,effect:allow/deny}],requests:[{id,token,resource,action}]}、schema_compatibility结果、session_replay结果。所有ID各自唯一，未知parent ValueError；组继承允许环，计算可达闭包直到不再增长，合并角色。只承认active_tokens；token中未知组ValueError。模式不兼容时全部deny(reason=schema)，无活动token则deny(reason=session)，否则匹配角色及区分大小写fnmatchcase资源/动作；任何deny规则优先，无deny且有allow才allow，默认deny。胜出规则按同effect中ID字典序最小者。输出 {decisions:[{id,effect,reason:schema/session/rule/default,rule_id:str或null,roles:list[str]}],allow,deny}，decisions保留请求顺序，roles排序。

补充边界：schema/session前置失败时roles=[]、rule_id=null；schema失败优先于session失败。合法schema和活动token下，roles是其所有组及父组的完整角色并集，即使最终default deny也返回roles。不要套用policy_precedence的priority/specificity：本operation只在匹配规则中先deny，再按同effect的id最小选胜者。未知活动token组即使schema不兼容也属于输入错误；没有被活动token引用的请求token不报未知ID，而按session拒绝。

局部检查命令：`python3 authorization/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`身份联邦迁移`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
