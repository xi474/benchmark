# 证书轮换准备：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`products/trust_graph/`、`products/trust_policy/`、`products/renewal_windows/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

本题强化operation（certificate_schedule, trust_paths）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

### 公告覆盖的完整共用定义

输入 {clients:[{id,weight:int>=0,deadline:int>=0,mandatory:bool}],windows:[{id,start:int>=0,end:int>start,cost:int>=0,clients:list[client_id]}],budget:int>=0,cooldown:int>=0}。重复ID/窗口内重复client/未知client、非法类型ValueError。选择互不重叠且前end+cooldown<=后start、总cost<=budget的窗口；仅end<=client.deadline的覆盖有效；同client价值只计一次。先要求覆盖所有mandatory客户，在可行集合中最大化覆盖weight之和、再最小化cost、最后取排序窗口ID列表字典序最小者。无可行集合返回feasible=false、空selected/completion、value/cost为0；成功输出 {feasible,selected,value,cost,completion:{client_id:最早有效公告end}}。空输入成功空解。实例窗口数<=16，不能用逐窗口价值相加的贪心替代集合覆盖。
completion仅包含确实按期限覆盖的客户，不是全部客户的占位映射；对同一客户取所有选中且有效窗口的最早end。窗口即使包含过期客户仍可被选，只是该客户不计覆盖。列表平局遵循通常字典序（相同前缀时较短者优先），不额外以窗口数量为优化目标。先校验全部输入，再优化，不得借过滤掩盖非法窗口或客户。

## 各组件的完整业务规则

### products/trust_graph — 撤销与有效期约束的最宽信任路径

operation：`trust_paths`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {now:int>=0,nodes:[{id,expires:int>=0,revoked:bool}],roots:list[id],edges:[{issuer,subject,expires:int>=0}]}；节点ID唯一，根/边端点必须存在，同issuer/subject重复边ValueError。删除revoked或expires<=now的节点和expires<=now的边；有向环合法。对每可达节点，选择根到它的路径，使所有节点/边expires的最小值最大；再选最少边数，再选完整ID路径字典序最小。输出 {trusted:[{id,path:list[id],valid_until:int}],untrusted:list[id]}，列表按id。不能只做最短路，也不能因某条路径被撤销而忽略仍有效替代路径。空图合法。

补充边界：边方向为issuer→subject；valid_until是路径所有节点与边expires的最小值，包含根和目标节点；等于now视为失效。先最大valid_until，再最少边数，最后比较完整ID路径，不将最短路径优先于有效期。根本身可以有长度0的信任路径；roots重复引用按集合处理；untrusted包含所有不可达、被撤销和过期节点。原节点标识保持原值，不小写。

局部检查命令：`python3 products/trust_graph/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/trust_policy — 通配策略优先级

operation：`policy_precedence`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{rules:[{id,resource:glob,action:glob,priority:int,effect:allow/deny}],requests:[{resource,action}]}。rule id去空白检查非空及唯一，但胜出rule_id、规则模式使用原字符串；resource/action为非空字符串，请求的resource/action去首尾空白后匹配。使用区分大小写的fnmatchcase glob，支持*、?和[]。匹配规则依次按priority降序、specificity降序、deny优先、原id字典序升序决定胜者；specificity为resource+action字符串中不属于*?[]的字符数，不是仅统计资源路径。无匹配时deny、rule_id=null。result={decisions:[{resource,action,effect,rule_id}],allow,deny}；decisions保持请求顺序，包括重复请求；不从输出删去deny。空请求返回[]与两个0；无规则时每条请求默认deny。

局部检查命令：`python3 products/trust_policy/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/renewal_windows — 受信任与策略门控的轮换覆盖

operation：`certificate_schedule`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为notice_coverage本地schema（client ID即证书ID）、trust_paths结果、policy_precedence结果。只有trusted证书且存在该resource、action=rotate、effect=allow的策略decision才算可覆盖；其他client从每个窗口覆盖集合中排除，但mandatory义务不能删除。然后精确执行notice_coverage的期限/冷却期/预算/覆盖价值优化，返回相同schema。改变任一上游可能使原可行方案不可行，不能把deny证书仍算作已覆盖。

补充边界：先校验完整本地coverage输入，再过滤各窗口中的客户集合；不能过滤掉非法id来规避输入错误。trusted按证书id判断，策略取decision.resource与证书id相等、action准确为rotate且effect=allow的集合交集；不以规则文本代替已经计算出的decisions。只过滤窗口覆盖列表，保留全部clients及其mandatory义务、weight/deadline和原窗口cost/时间。completion/value不得计入被过滤的证书。无可行覆盖返回false及全部空/零字段。

局部检查命令：`python3 products/renewal_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`证书轮换准备`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
