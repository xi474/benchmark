# 流处理检查点恢复：接口与业务规格

修复缺失实现，依据真实输入生成可重建、确定性的JSON产物。以下业务算法的节点、边、窗口或资源是被实现程序的数据语义，不是Agent执行计划。

## 实现范围与保护边界

组件目录为`event_codec/`、`checkpoint_restore/`、`diagnostic_logs/`。每个组件实现model.py、transform.py、render.py；根目录实现run_all.py、final_report.py。可添加必要的私有辅助模块。
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

### event_codec — 新旧事件编码兼容

operation：`event_decode`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{events:[对象或JSON字符串],checkpoints:任意JSON值}。每个event解码后必须是对象；字段partition优先于旧topic、offset优先于旧sequence、epoch优先于旧generation（都缺省时epoch=0）、committed优先于旧ack（都缺省时false）。新字段存在但非法时不能回退旧字段。partition去空白后非空；offset/epoch为整数>=0，committed必须是布尔。输出result={events:[{partition,offset,epoch,committed}],checkpoints:原checkpoints的深拷贝}，events按(partition,offset,epoch,committed)升序，保留重复事件。这里不按修订去重、不验证或执行checkpoints，交给消费它的组件。非法JSON或解码后非对象ValueError。空events仍原样带回checkpoints。

局部检查命令：`python3 event_codec/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### checkpoint_restore — 连续确认偏移恢复

operation：`checkpoint_replay`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

首输入{checkpoints:[{partition:非空str,offset:int>=-1,epoch:int>=0}],events:[{partition:非空str,offset:int>=0,epoch:int>=0,committed:bool}]}。partition去空白；本operation没有event_decode的旧字段别名或缺省值。对checkpoint校验全部(partition,epoch)版本，同版本offset冲突ValueError，按partition选最大epoch，不以offset最大代替。事件校验全部(partition,offset,epoch)，相同版本committed冲突ValueError，再为每(partition,offset)选最大epoch。partition并集包括只在checkpoint或event出现者，按字典序处理；无checkpoint时(epoch,offset)=(0,-1)。从checkpoint.offset+1起连续应用：该offset存在、选中事件epoch>=checkpoint.epoch且committed=true才前进；首缺口/旧epoch/未提交事件立即停止。result={next_offsets:{partition:停止处offset},applied:["partition:offset"],pending:{partition:[offset...]}}。applied按partition再offset顺序；pending是该partition所有选中事件中offset>=next_offset者的offset升序，包含未提交或旧epoch事件。完全空输入返回两个空映射及空applied。低版本冲突即使会被新版本覆盖也必须报错。

局部检查命令：`python3 checkpoint_restore/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

### diagnostic_logs — 混合格式日志与脱敏

operation：`log_compatibility`。具体输入文件、输入顺序和输出路径读取本目录contract.json；下文只定义文件内容的解释，不另给任务调度关系。

输入{lines:[字符串或对象]}。字符串去左空白以{开始时必须作为JSON解析且结果为对象，坏JSON不能当纯文本兜底；其他纯文本按strip后首次空白分成level/message，只有level时message为空，纯空白行忽略。对象优先level而非severity、message而非msg；新字段存在但非法不回退。level去空白小写，warning映射warn，仅debug/info/warn/error合法；message必须是字符串，对象message不另做strip。消息内不区分大小写匹配单词边界的token/password/secret，允许等号两侧空白；值可为单双引号包围的串或到空白/逗号/分号为止的非空串，将整个键值匹配替换成小写key=[REDACTED]。输出result={lines:["LEVEL message"],counts:{规范化小写level:条数}}，lines保留输入有效行次序；counts键排序，仅出现过的level存在，空输入为[]和{}。不按消息内容去重。

局部检查命令：`python3 diagnostic_logs/check_module.py`。运行检查时，契约引用的输入与本组件输出必须真实存在；缺少条件时先完成实际所需的工作，不能吞掉错误或跳过检查。

## JSON产物、集成与最终报告

所有写出的JSON文件采用UTF-8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False，末尾加一个真实换行字符。紧凑摘要序列化与文件展示格式不同。
`run_all.py`定位工作区，依据真实文件接口完成全部必要计算，执行已有集成与最终报告。不能用文件名排序代替执行条件，不能依赖旧outputs；各子进程失败传播非零退出码。已有`python3 integrate.py`读取组件产物生成`outputs/core_manifest.json`，其完整结构为`{"components": {组件名: 该组件的result}}`。

`final_report.py`读取并解析完整`outputs/core_manifest.json`对象，写`outputs/final_report.json`，恰有title、component_count、sha256、attention四个字段。title准确为`流处理检查点恢复`；component_count为core_object["components"]的键数。
sha256的输入对象是完整core_object，包含外层components键；不是仅core_object["components"]、不是原文件字节、不是多个文件摘要拼接。序列化准确为`json.dumps(core_object, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")`，不加文件末尾换行，然后求SHA-256小写hex。
attention是组件名去重排序列表：对每个result，blocked为真、feasible或compatible显式为false、deny>0、score_total>=20中任一条件成立即列入；不存在的字段不触发，不能把空列表、空对象或数值0等同于显式false。每个组件至多列一次。

## 验收与执行边界

在工作区运行`python3 check.py`。公开检查会清理旧outputs、完成适用的材料物化、运行run_all并检查模块与输出结构；公开通过不代表全部业务语义正确。外部只读验证器另外检查受保护文件、全部预期产物、规范序列化及接口边界输入。
给Agent的材料只有本任务TASK.md和workspace。作者参考实现、评分器、审计记录、历史输出和其他任务不得作为工作区或模型上下文输入。
