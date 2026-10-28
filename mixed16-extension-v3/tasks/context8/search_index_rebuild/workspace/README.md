# 搜索索引重建

解析字段重命名图并恢复分片修订，按副本仲裁与预算优化索引切换。本任务使用 Python 标准库，必须由输入重新计算，不能硬编码结果。

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

### mapping_compat — 重命名图解析与模式迁移

输入：`inputs/mapping_compat.json`；输出：`outputs/mapping_compat.json`。参数以本组件 contract.json 为准。

输入 {old:list[field],new:list[field],renames:[{from:str,to:str}]}，field同schema_compatibility。from唯一，重命名形成有向图，链式解析至最终名字，任何环（包括未被old字段使用的环）ValueError；不同old字段归一至同终点ValueError。将old字段重命名后，按schema_compatibility规则判断删除、增加、int->float拓宽、required/default；输出 {compatible,changes,field_map:{old_name:terminal_name}}。field_map按原字段名，changes排序同原算法；空输入可行。

局部验收：`python3 mapping_compat/check_module.py`（先生成依赖及本组件输出）。

### shard_replay — 分片日志缺口与墓碑恢复

输入：`inputs/shard_replay.json`；输出：`outputs/shard_replay.json`。参数以本组件 contract.json 为准。

输入 {replicas:[{id,shard,host,checkpoint:int>=-1,documents:[{id,version:int>=0,fields:dict}]}],events:[{replica,offset:int>=0,epoch:int>=0,op:upsert/delete,id,version:int>=0,fields:dict(仅upsert)}]}。replica ID和初始document ID分别唯一，未知replica ValueError。相同(replica,offset)取最高epoch；任意同epoch不同内容冲突ValueError，相同内容重复允许。从checkpoint+1逐个处理连续offset，首个缺口停止。每document只接受更高version；相同version相同内容幂等、不同内容（包括delete与upsert）冲突；较低version忽略，墓碑保留版本防止旧upsert复活。输出 {replicas:[{id,shard,host,applied_offset,documents:[{id,version,fields}],tombstones:{id:version},sha256}]}，副本与documents按id，摘要对documents的UTF-8紧凑sort_keys JSON计算SHA256；空副本表返回空列表。

局部验收：`python3 shard_replay/check_module.py`（先生成依赖及本组件输出）。

### cutover_plan — 副本仲裁与预算最优切换

输入：`inputs/cutover_plan.json`, `outputs/mapping_compat.json`, `outputs/shard_replay.json`；输出：`outputs/cutover_plan.json`。参数以本组件 contract.json 为准。

输入顺序为 {partitions:[{id,quorum:int>=1,value:int>=0,target_sha256:str,target_offset:int>=-1}],candidates:[{id,replica,cost:int>=0}],budget:int>=0}、schema_migration结果、shard_replay结果。各数组ID唯一；未知replica或分片、同replica多个candidate、非法digest ValueError。只有摘要等于对应partition.target_sha256且applied_offset>=target_offset的副本候选可用。选择总cost<=budget的候选集合；同partition同host最多一个、每partition所选数只能为0或恰好quorum。最大化已满足partition.value总和，再最小cost，再排序candidate ID列表字典序最小。模式不兼容返回blocked=true及空选择；否则输出 {blocked:false,selected,partitions:已满足分片ID排序,value,cost}。<=14候选，需精确优化，不能逐副本贪心或用副本数量替代独立host仲裁。

局部验收：`python3 cutover_plan/check_module.py`（先生成依赖及本组件输出）。

## 集成与交付

补齐 run_all.py，从任意当前目录启动时定位工作区；执行所有必要组件、已有集成命令与 final_report.py。每个子进程失败必须传播非零退出码；不得吞掉失败、跳过尚未生成的依赖或复用旧 outputs。

已有 integrate.py：`python3 integrate.py` 读取所有组件产物写 outputs/core_manifest.json，内容为 {components:{组件名:result}}。multistage 的 `python3 integrate.py domains` 合并 domains 记录并按(source,id)去重、冲突报错，写 outputs/domain_core.json；仅契约引用此文件时才需要该中间产物。

补齐 final_report.py，读取 core_manifest，写 outputs/final_report.json：{title:'搜索索引重建',component_count:组件数,sha256:核心对象摘要,attention:需要关注的组件名排序列表}。摘要对 json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False) 的 UTF-8 字节计算 SHA-256。attention 包含 result.blocked 为真，或 feasible/compatible 显式为假，或 deny>0，或 score_total>=20 的组件；不存在的字段不触发。

## 验收

`python3 check.py` 是可见本地冒烟检查：清理旧 outputs、物化（如适用）、执行 run_all、检查输出结构并运行局部检查。它不包含完整预期结果，也不决定正式得分。正式评分由工作区外的只读 verifier 校验所有受保护文件（包括 check.py 自身）的可信哈希、全部产物与隐藏的边界/变异输入。不要把 _authoring/、verifier/、验证记录或上级目录挂载给被测代理。

## 运行方式

将本 TASK.md 与对应 workspace 单独交给代理。完成实现后，在工作区运行 `python3 check.py`。正式评测命令及信任边界见数据集根 README，代理只需完成此工作区。
