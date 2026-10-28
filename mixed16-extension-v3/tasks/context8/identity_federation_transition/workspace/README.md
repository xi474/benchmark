# 身份联邦迁移

比较声明模式并重放令牌轮换与撤销，结合组继承闭包生成授权审计。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

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

### claims — 字段模式兼容

输入：`inputs/claims.json`；输出：`outputs/claims.json`。参数以本组件 contract.json 为准。

输入 {old:list[field],new:list[field]}，field={name:非空str,type:int/float/str/bool,required:bool,default?:任意JSON值}；同一模式重复字段名ValueError。删除字段一定breaking；新增required且无default为breaking；类型变化仅int->float兼容；optional->required仅有default时兼容。输出 {compatible:bool,changes:[{field,code:removed/added/type/required,breaking:bool}]}；字段按name排序，同字段type在required之前，未变化不输出。空模式合法。

局部验收：`python3 claims/check_module.py`（先生成依赖及本组件输出）。

### sessions — 乱序令牌轮换及传递撤销

输入：`inputs/sessions.json`；输出：`outputs/sessions.json`。参数以本组件 contract.json 为准。

输入 {now:int>=0,events:[{id,ts:int>=0,kind:issue/refresh/revoke,token:str,...}]}，event ID唯一，按(ts,kind优先级revoke<issue<refresh,id)处理，ts>now的事件不执行但仍校验schema。issue含subject非空str、expires:int>ts、groups:list[str]；refresh含parent:str、expires:int>ts；revoke不带额外必需字段。token只能issue/refresh一次，否则ValueError。revoke可先于签发，撤销标记永久保留；刷新父令牌必须已签发、在刷新时未到期且其祖先未撤销，否则子令牌被签发但永久无效。有效refresh继承subject/groups，轮换后父令牌标为superseded且不能再次刷新；祖先之后撤销也使全部后代无效，但祖先自然到期或被轮换不使已签发子令牌失效。输出 {active_tokens:[{token,subject,groups,expires}],invalid_tokens:list[token],revoked:list[token]}；now>=expires失效，各列表按token排序，groups去重排序。缺字段、非法类型ValueError。

局部验收：`python3 sessions/check_module.py`（先生成依赖及本组件输出）。

### authorization — 组继承闭包与跨组件授权

输入：`inputs/authorization.json`, `outputs/claims.json`, `outputs/sessions.json`；输出：`outputs/authorization.json`。参数以本组件 contract.json 为准。

输入顺序为 {groups:[{id,parents:list[group_id],roles:list[str]}],rules:[{id,role,resource:glob,action:glob,effect:allow/deny}],requests:[{id,token,resource,action}]}、schema_compatibility结果、session_replay结果。所有ID各自唯一，未知parent ValueError；组继承允许环，计算可达闭包直到不再增长，合并角色。只承认active_tokens；token中未知组ValueError。模式不兼容时全部deny(reason=schema)，无活动token则deny(reason=session)，否则匹配角色及区分大小写fnmatchcase资源/动作；任何deny规则优先，无deny且有allow才allow，默认deny。胜出规则按同effect中ID字典序最小者。输出 {decisions:[{id,effect,reason:schema/session/rule/default,rule_id:str或null,roles:list[str]}],allow,deny}，decisions保留请求顺序，roles排序。

局部验收：`python3 authorization/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'身份联邦迁移',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
