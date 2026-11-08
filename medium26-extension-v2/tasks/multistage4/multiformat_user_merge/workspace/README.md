# 多格式用户合并与完整冲突报告：接口与完整规格

读取JSON、CSV、JSONL用户源，分别输出records数组，再按字段优先级合并用户目录和完整冲突证据。

## 环境与实现范围

Python 3.11及以上，仅标准库；本地合成输入，无GPU、训练、网络、真实账号或实时等待。所有时间按本题显式规则处理，禁止读取当前日期替代输入日期。

domains/负责不同领域/表示，views/消费领域产物，保留真实的分叉与汇合；组件数由业务决定。

组件实现model.py、transform.py、render.py，以及根run_all.py和final_report.py；可新增私有辅助模块。未提供的实现文件需要自行创建。

README.md、TASK.md、inputs/、contract.json、check_module.py、check.py、integrate.py以及适用的materialize.py、__init__.py、parser.py不可修改。初始输入和契约为任务规格，不是可以修正的错误数据。

## 稳定接口与通用边界

- model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。

- transform.transform(payloads:list,contract:dict)：payloads按contract.inputs顺序，数量必须一致。返回恰好{"name":contract["name"],"result":算法结果对象}；本说明中的输出均指result，不额外套一层封装。

- 当输入对象键恰为name/result时，仅其result为业务输入；其他对象原样解释。不修改payloads/contract（包括嵌套值），不硬编码公开输入或上游结果。

- render.build_component(root:Path,contract_path:Path)：从给定root读取所有输入，调用transform并返回封装。执行python3 <组件目录>/render.py时，将封装写入contract.output；必须支持任意当前目录。缺文件或子命令失败须失败。

- context包另外保留<package>.parser.parse(payloads,contract)，返回与transform完全一致的封装。不要修改稳定parser来绕过实现。

- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。未知额外字段可忽略，但其中非有限JSON仍非法。所有合法空集/无解按照各operation输出。

- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。

- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。

## 各组件业务规则

### domains/json_users

operation：`users_json`。输入文件及顺序见`domains/json_users/contract.json`，输出为`outputs/json_users.json`。

输入含json_text:str，其内容为对象数组。每行规范为{id:str,name?,email?,joined?}。user_id优先id；ID为非空str或int（bool非法），str.strip后返回。name/full_name、email/mail、joined/joined_at使用新字段存在优先；null/缺失不赋值，空串是有效值。joined非空时只接受YYYY-MM-DD或DD/MM/YYYY并转ISO日期。同源重复ID按原顺序逐字段最后一个存在值胜出。输出{records:按ID字典序}；未知字段忽略。records必须是JSON数组list[object]，不能是以ID为键的对象；每个元素含id:str和存在的name/email/joined字段，按id字符串字典序升序，空结果为{"records":[]}。

局部检查：`python3 domains/json_users/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/csv_users

operation：`users_csv`。输入文件及顺序见`domains/csv_users/contract.json`，输出为`outputs/csv_users.json`。

输入含csv_text:str，CSV首行为表头，支持标准双引号转义/逗号/嵌入换行，必须有id或user_id列；列名唯一且无缺列/额外列。规范与users_json相同，但CSV空单元格视为缺失值（不清空旧值）。空文本返回空records；重复源ID逐字段最后存在值胜出。输出records同样必须是按id字符串字典序升序的对象数组，空结果为{"records":[]}，不是{}。

局部检查：`python3 domains/csv_users/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/jsonl_users

operation：`users_jsonl`。输入文件及顺序见`domains/jsonl_users/contract.json`，输出为`outputs/jsonl_users.json`。

输入含jsonl_text:str。忽略纯空白行，每个其余物理行必须是一个JSON对象；坏JSON立即ValueError。其余规范、同源重复和空串规则同users_json，输出{records:按ID排序}。records必须是对象数组list[object]，按id字符串字典序升序；空结果为{"records":[]}，不是以ID为键的对象。

局部检查：`python3 domains/jsonl_users/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/directory

operation：`users_merge`。输入文件及顺序见`views/directory/contract.json`，输出为`outputs/directory.json`。

输入依次为JSON、CSV、JSONL规范记录；来源名固定json/csv/jsonl。逐字段选首个存在值，按该来源优先级，null已在解析层移除，空串参与优先级。输出 {users:[合并用户按id],conflicts:[{id,field,values:[{source,value}]}]}；不同来源中同字段出现两个以上不同值时列出全部来源证据，conflicts按(id,field)。包含仅出现在低优先级来源的用户。三个上游输入的result.records均为上述对象数组；不能按ID映射对象解释。

局部检查：`python3 views/directory/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'多格式用户合并与完整冲突报告'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

