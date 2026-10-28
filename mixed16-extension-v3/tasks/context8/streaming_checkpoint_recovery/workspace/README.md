# 流处理检查点恢复

兼容事件编码并恢复已确认的连续偏移，在缺口处停止，另行生成脱敏诊断日志。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

## 不可修改文件

README.md、TASK.md、check.py、integrate.py、inputs/、任何 contract.json 和 check_module.py 不可修改。context 包的 __init__.py、parser.py 是稳定接口，也不可修改。linux 任务还保护 materialize.py 及其物化的输入、契约和局部检查。仅实现/修复各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；可添加私有辅助模块。

## 组件接口

契约字段顺序统一为 name、operation、inputs、output、threshold，再列算法参数。inputs 是必要文件接口，执行依赖需从现有接口中推导；没有计划 DAG、调度标签或隐藏的完整任务计划。所有组件输出统一封装 {"name":契约name,"result":算法结果对象}，下面的输出 schema 均指 result。JSON 采用 UTF-8、sort_keys=True、两空格缩进、末尾换行，禁止非有限值。

- model.load_payload(path:Path)：读取 JSON 对象或数组，其他顶层类型或非法 JSON 抛 ValueError。字段验证在 transform 中完成。

- transform.transform(payloads:list, contract:dict)：按 inputs 顺序接收已读取的数组或对象，返回上述封装；若输入为另一个组件封装，读取其 result。不得修改 payloads 或 contract。所有未声明的缺字段、非法类型、冲突均抛 ValueError；bool 不能作为整数或数值。

- render.build_component(root:Path, contract_path:Path)：读取契约与全部输入，调用 transform 并返回封装；执行 python3 <组件目录>/render.py 应写到 output，支持任意当前目录。缺失依赖文件必须失败。

context 包保留 parser.parse(payloads,contract)，返回与 transform 一样的封装，调用方使用 <package>.parser 导入。

## 各组件规则

### event_codec — 新旧事件编码兼容

输入：`inputs/event_codec.json`；输出：`outputs/event_codec.json`。参数以本组件 contract.json 为准。

输入 {events:list[dict或JSON字符串],checkpoints:list}。partition或旧topic为非空str；offset或旧sequence为int>=0；epoch或旧generation为int>=0，缺省0；committed或旧ack为bool，缺省false。新字段存在时优先使用新字段。输出 {events:[{partition,offset,epoch,committed}],checkpoints}；events按(partition,offset,epoch,committed)排序，保留重复给下游处理；checkpoints原样传递。非法JSON、缺字段或非法类型ValueError；空events合法。

局部验收：`python3 event_codec/check_module.py`（先生成依赖及本组件输出）。

### checkpoint_restore — 连续确认偏移恢复

输入：`outputs/event_codec.json`；输出：`outputs/checkpoint_restore.json`。参数以本组件 contract.json 为准。

输入 {checkpoints:[{partition,offset:int>=-1,epoch:int>=0}],events:[{partition,offset:int>=0,epoch:int>=0,committed:bool}]}。每partition取最高epoch的checkpoint，同epoch不同offset冲突。每(partition,offset)取最高epoch事件，同epoch不同committed冲突；同内容重复允许。分区按字典序；从checkpoint.offset+1（缺省epoch=0/offset=-1）起，只重放连续、committed=true且epoch>=checkpoint.epoch的事件，遇缺口/未确认/旧epoch即停止。输出 {next_offsets:{partition:int},applied:[partition+":"+offset],pending:{partition:list[offset]}}；pending为停止位置起已有offset排序列表，applied先分区后offset。空输入输出空字典和列表。

局部验收：`python3 checkpoint_restore/check_module.py`（先生成依赖及本组件输出）。

### diagnostic_logs — 混合格式日志与脱敏

输入：`inputs/diagnostic_logs.json`；输出：`outputs/diagnostic_logs.json`。参数以本组件 contract.json 为准。

输入 {lines:list[纯文本行、JSON字符串或对象]}。纯文本首词为级别，其余为message；对象读取level或旧severity、message或旧msg。level不区分大小写，warning统一warn，只允许debug/info/warn/error。空白纯文本跳过；message必须str。将token/password/secret后等号及可选空白所连的非空值（双引号串、单引号串或直到空白/逗号/分号）替换为小写键=[REDACTED]。输出 {lines:list[大写level+空格+脱敏message],counts:{小写level:int}}；保留输入行序，空输入输出[]/{}。非法JSON、非法级别/字段ValueError。

局部验收：`python3 diagnostic_logs/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'流处理检查点恢复',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
