# 支付清算对账：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`settlements/`、`settlement_windows/`、`payment_traces/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

## 各组件的完整业务规则

### settlements — 新旧清算事件兼容

operation：`settlement_decode`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{events:[对象或JSON字符串]}。每个event必须有id:非空str、ts或旧timestamp:int>=0、key或旧account:非空str、value或旧amount:有限int/float；revision缺省0且为int>=0。新字段存在就优先使用，即使其值为null或非法，也不能回退旧字段。id去空白、key去空白并小写；bool不是合法数值。输出result={events:[{id,revision,ts,key,value}]}，按(id,revision,ts,key,value)升序，保留重复项及各修订，不在本组件选最新版。空输入为events=[]；非法JSON、非对象、缺必要字段或非法数值ValueError。

局部检查命令：`python3 settlements/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### settlement_windows — 修订去重与分桶分位数

operation：`event_windows`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{events:[{id:非空str,revision:int>=0,ts:int>=0,key:非空str,value:有限int/float}]}，window_size是正整数。id去空白，key去空白小写；bool/NaN/Infinity非法。先检查所有(id,revision)的规范化内容，一旦同版本冲突即ValueError，不能因为它不是最新版而跳过；相同副本去重。再按id取最大revision。按(start,key)分组，start=(ts//window_size)*window_size，end=start+window_size，窗口半开。result={windows:[{start,end,key,count,sum,p95}],event_count:按id选最新版后的总数}，windows按(start,key)升序。每组p95为升序value的第ceil(0.95*n)项（从1计数），不能插值；sum保留合法数值运算结果。没有事件时windows=[]、event_count=0。

局部检查命令：`python3 settlement_windows/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### payment_traces — 扁平与嵌套链路关联

operation：`trace_correlation`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{spans:[span]}；span有id/service非空str、duration为非负有限数字、error:bool，可有parent:id或null、children:span数组。递归展开；显式parent字段优先，包括显式null，未声明parent时才继承嵌套父id。id去空白作为节点标识，parent准确引用节点；重复id、未知parent、自环及一般环ValueError。每条根到节点路径长度为各节点duration之和，不使用时间戳；最大长度平局时取完整节点ID路径字典序最小。result={error_services,critical_path,duration,span_count}；error_services只包含error=true节点的service去空白小写后去重排序；span_count为展开节点总数。空图两个列表为空、duration=span_count=0。

局部检查命令：`python3 payment_traces/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`支付清算对账`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
