# 支付清算对账

兼容新旧清算事件，按修订去重并计算对账窗口，同时关联支付链路故障。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

## 不可修改文件

README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。

## 组件接口

契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。

- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。

- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。

- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。

context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。

## 各组件规则

### settlements — 新旧清算事件兼容

输入：`inputs/settlements.json`；输出：`outputs/settlements.json`。参数以本组件 contract.json 为准。

输入 {events:list[dict或JSON字符串]}。读取id:str、revision:int>=0（缺省0）、ts或旧timestamp:int>=0、key或旧account:非空str、value或旧amount:有限数字。新字段优先。规范化key为小写；输出 {events:[{id,revision,ts,key,value}]} 按(id,revision,ts,key,value)排序；保留修订交下游处理。bool不能作为数值，非法JSON/非有限值/缺字段ValueError。

局部验收：`python3 settlements/check_module.py`（先生成依赖及本组件输出）。

### settlement_windows — 修订去重与分桶分位数

输入：`outputs/settlements.json`；输出：`outputs/settlement_windows.json`。参数以本组件 contract.json 为准。

输入 {events:[{id:非空str,revision:int>=0,ts:int>=0,key:非空str,value:有限数字}]}，key去空白小写。每id取最高revision；相同revision的规范化记录不同则ValueError，相同记录去重。按floor(ts/window_size)*window_size分桶；输出 {windows:[{start,end,key,count,sum,p95}],event_count:去重条数}，windows按(start,key)排序。p95是升序值第ceil(.95*n)项，不能插值。bool/NaN/Infinity不是合法value；空输入为[]/0。

局部验收：`python3 settlement_windows/check_module.py`（先生成依赖及本组件输出）。

### payment_traces — 扁平与嵌套链路关联

输入：`inputs/payment_traces.json`；输出：`outputs/payment_traces.json`。参数以本组件 contract.json 为准。

输入 {spans:list[span]}。span含id、service非空str、duration:非负有限数字、error:bool，可有parent:id或null、children:list[span]；显式parent优先，否则嵌套父节点。展开后重复id、未知parent、环ValueError。路径duration为根到节点duration之和，不使用时间戳相减；相同duration取完整ID路径字典序最小者。输出 {error_services:小写去重排序服务列表,critical_path:list[id],duration:number,span_count:int}；空图为空列表和零。

局部验收：`python3 payment_traces/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'支付清算对账',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
