# 可观测数据保留升级：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`products/archive_logs/`、`products/retention_windows/`、`products/retention_policy/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

本题强化operation（retention_audit, retention_optimizer）还要求整个payloads中的嵌套JSON值有限，即使字段未参与业务计算，内含NaN/Infinity也抛ValueError。

### 静态策略的完整共用定义

输入{rules:[{id,resource:glob,action:glob,priority:int,effect:allow/deny}],requests:[{resource,action}]}。rule id去空白检查非空及唯一，但胜出rule_id、规则模式使用原字符串；resource/action为非空字符串，请求的resource/action去首尾空白后匹配。使用区分大小写的fnmatchcase glob，支持*、?和[]。匹配规则依次按priority降序、specificity降序、deny优先、原id字典序升序决定胜者；specificity为resource+action字符串中不属于*?[]的字符数，不是仅统计资源路径。无匹配时deny、rule_id=null。result={decisions:[{resource,action,effect,rule_id}],allow,deny}；decisions保持请求顺序，包括重复请求；不从输出删去deny。空请求返回[]与两个0；无规则时每条请求默认deny。

## 各组件的完整业务规则

### products/archive_logs — 混合格式日志与脱敏

operation：`log_compatibility`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{lines:[字符串或对象]}。字符串去左空白以{开始时必须作为JSON解析且结果为对象，坏JSON不能当纯文本兜底；其他纯文本按strip后首次空白分成level/message，只有level时message为空，纯空白行忽略。对象优先level而非severity、message而非msg；新字段存在但非法不回退。level去空白小写，warning映射warn，仅debug/info/warn/error合法；message必须是字符串，对象message不另做strip。消息内不区分大小写匹配单词边界的token/password/secret，允许等号两侧空白；值可为单双引号包围的串或到空白/逗号/分号为止的非空串，将整个键值匹配替换成小写key=[REDACTED]。输出result={lines:["LEVEL message"],counts:{规范化小写level:条数}}，lines保留输入有效行次序；counts键排序，仅出现过的level存在，空输入为[]和{}。不按消息内容去重。

局部检查命令：`python3 products/archive_logs/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/retention_windows — 法律保留与分类配额的分组背包

operation：`retention_optimizer`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入 {archives:[{id,category,hold:bool,modes:[{id,bytes:int>=0,value:int>=0}]}],budget:int>=0,minimums:{category:int>=0}}。archive ID和同archive的mode ID唯一，空mode数组允许；每archive选择至多一个mode，hold=true必须选一个；各category选中archive数量>=minimums。总bytes<=budget，精确最大化总value，再最小bytes，再按(archive,mode)排序列表字典序最小。输出 {feasible,selected:[{archive,mode}],bytes,value}；无解false/[]/0/0。<=10档案、每个<=3模式；可以DP/回溯，不能按value/bytes贪心或删除法律保留档案。

补充边界：minimums按选中的archive数量计数，不按mode数量或value求和；同archive至多一个mode，每个法律保留archive必须选一个mode，hold且modes=[]使整体无解。minimums里没有对应archive的类别若要求正数，也使整体无解；零要求不产生义务。selected排序键为(archive,mode)，bytes和值只对选中模式累加；即使value相同，也先比较更少bytes，再比较整个selected元组列表。空archives且所有配额为0时是可行空解。

局部检查命令：`python3 products/retention_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### products/retention_policy — 保留计划与日志覆盖联合授权

operation：`retention_audit`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入顺序为 {rules:policy_precedence规则数组,requests:[{id,archive,resource,action}]}、log_compatibility结果、retention_optimizer结果。request ID唯一。脱敏后的lines以空白/行界提取request=<id>与archive=<id>标记；相同request重复出现或未知request/标记冲突ValueError。每请求按优先级依次判断：计划不可行deny(plan)，archive未保留deny(retention)，无该request且archive相同的审计行deny(audit)，否则按policy_precedence决策，reason=policy。输出 {decisions:[{id,effect,reason,rule_id}],allow,deny}，顺序同requests；不能只运行静态策略忽略保留结果或审计覆盖。

补充边界：从每个脱敏后输出行分别提取第一个空白边界request=标识与archive=标识。没有request标记的行忽略，即使有archive；有request则必须已知、未在之前行出现且archive匹配该请求，否则ValueError。标记不是按任意子串匹配，标点不会自动剥除。相同archive可对应多个不同request。前置拒绝(plan/retention/audit)返回rule_id=null，即使静态策略原本有匹配规则；全部合法策略仍须校验。日志counts不用于判断审计覆盖，必须实际读lines。

局部检查命令：`python3 products/retention_policy/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`可观测数据保留升级`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
