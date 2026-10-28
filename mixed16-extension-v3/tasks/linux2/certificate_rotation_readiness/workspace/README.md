# 证书轮换准备

物化工具并计算撤销感知的最宽信任路径，联合策略优化证书轮换覆盖。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

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

### products/trust_graph — 撤销与有效期约束的最宽信任路径

输入：`inputs/trust_graph.json`；输出：`outputs/trust_graph.json`。参数以本组件 contract.json 为准。

输入 {now:int>=0,nodes:[{id,expires:int>=0,revoked:bool}],roots:list[id],edges:[{issuer,subject,expires:int>=0}]}；节点ID唯一，根/边端点必须存在，同issuer/subject重复边ValueError。删除revoked或expires<=now的节点和expires<=now的边；有向环合法。对每可达节点，选择根到它的路径，使所有节点/边expires的最小值最大；再选最少边数，再选完整ID路径字典序最小。输出 {trusted:[{id,path:list[id],valid_until:int}],untrusted:list[id]}，列表按id。不能只做最短路，也不能因某条路径被撤销而忽略仍有效替代路径。空图合法。

局部验收：`python3 products/trust_graph/check_module.py`（先生成依赖及本组件输出）。

### products/trust_policy — 通配策略优先级

输入：`inputs/trust_policy.json`；输出：`outputs/trust_policy.json`。参数以本组件 contract.json 为准。

输入 {rules:[{id,resource:通配str,action:通配str,priority:int,effect:allow/deny}],requests:[{resource:str,action:str}]}；rule id去空白后不得重复。使用区分大小写的fnmatchcase，两字段同时匹配才有效。按priority降序、resource+action中不属于*?[]的字符数降序、deny优先、id字典序选胜者；无匹配默认deny且rule_id=null。输出 {decisions:[{resource,action,effect,rule_id}],allow:int,deny:int}；decisions保留请求顺序，空输入为[]/0/0。非法规则字段ValueError。

局部验收：`python3 products/trust_policy/check_module.py`（先生成依赖及本组件输出）。

### products/renewal_windows — 受信任与策略门控的轮换覆盖

输入：`inputs/renewal_windows.json`, `outputs/trust_graph.json`, `outputs/trust_policy.json`；输出：`outputs/renewal_windows.json`。参数以本组件 contract.json 为准。

输入顺序为notice_coverage本地schema（client ID即证书ID）、trust_paths结果、policy_precedence结果。只有trusted证书且存在该resource、action=rotate、effect=allow的策略decision才算可覆盖；其他client从每个窗口覆盖集合中排除，但mandatory义务不能删除。然后精确执行notice_coverage的期限/冷却期/预算/覆盖价值优化，返回相同schema。改变任一上游可能使原可行方案不可行，不能把deny证书仍算作已覆盖。

局部验收：`python3 products/renewal_windows/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'证书轮换准备',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

先运行 `python3 materialize.py`；该脚本校验内嵌物化清单的 SHA-256，生成 inputs/、products/ 的契约、检查与缺失实现占位。重复执行会保留实现，只核对受保护生成文件；冲突时失败。随后检查新出现的三个产品目录并实现工具。仅在物化完成后，产品分支才可执行。

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
