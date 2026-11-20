# MARC 作者标题、语言和主题导入：接口与完整规格

从有限 MARC XML 字段中独立提取作者/标题的替代文字链接、完整语言集合、分类主题计数，再形成同一书目记录。

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

### domains/reader

operation：`marc_xml_records`。输入文件及顺序见`domains/reader/contract.json`，输出为`outputs/reader.json`。

输入{xml:str,language_codes:[唯一三字母小写代码]}。只接受MARC XML的collection或record根（可带标准namespace），禁DOCTYPE/ENTITY。每record含唯一controlfield tag=001作为非空ID；controlfield tag为3位数字，同tag不重复，保留原文本（008依赖固定列）；datafield tag为3位数字，subfield code为一个字母或数字，保留子字段顺序和文本。未知XML元素/坏XML/重复记录ID报错。返回{records:[{id,controls:{tag:text},fields:[{tag,subfields:[{code,value}]}]}]}按id。不支持二进制MARC。

局部检查：`python3 domains/reader/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/names

operation：`marc_names_titles`。输入文件及顺序见`domains/names/contract.json`，输出为`outputs/names.json`。

输入为marc_xml_records结果。每条100用$a/$b连接作者名，245用$a/$b连接标题；词内空白折叠，首尾空格/斜线/逗号/冒号/分号移除，句点保留。100/245的$6必须为880-NN，880的$6为100-NN或245-NN（允许/后缀）；只有tag和NN双向匹配才增加替代文字，孤立880忽略。返回{records:[{id,authors:[{name,alternates:[去重排序]}],titles:[{title,alternates}]}]}，record按id，基础字段保持原顺序。

局部检查：`python3 domains/names/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/languages

operation：`marc_languages`。输入文件及顺序见`domains/languages/contract.json`，输出为`outputs/languages.json`。

输入依次为原输入、marc_xml_records。language_codes限定有效代码，必须3个小写字母。008存在时长度>=38，从下标35..37取一个代码；041的$a/$d/$h字符串去首尾空白后按每3字符切分，长度非3倍数报错。有效代码去重排序，未知代码忽略。返回{records:[{id,languages:[代码]}]}。不能把gerlat当一个代码。

局部检查：`python3 domains/languages/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/subjects

operation：`marc_subjects`。输入文件及顺序见`domains/subjects/contract.json`，输出为`outputs/subjects.json`。

输入为marc_xml_records。处理600/610/611/630/650/651，分别归people/organizations/meetings/works/topics/places。每字段$a/$b先连接为主标题，其$v/$x/$y/$z按出现顺序以" -- "连接为细分；每段空白折叠并剥首尾空格/斜线/逗号/冒号/分号，保留句点。同类型相同完整标题按字段出现次数计数，不按子字段数重复计。返回{records:[{id,subjects:{六类各自:[{value,count}]按value}}]}，无字段为空列表。

局部检查：`python3 domains/subjects/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/catalog

operation：`marc_catalog`。输入文件及顺序见`views/catalog/contract.json`，输出为`outputs/catalog.json`。

输入依次marc_names_titles、marc_languages、marc_subjects。三路记录ID集合必须完全相同且各路唯一；按id连接所有语义字段，返回{records:[{id,authors,titles,languages,subjects}],record_count}。不能按行号zip，不能丢缺少语言/主题的书目。

局部检查：`python3 views/catalog/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'MARC 作者标题、语言和主题导入'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

