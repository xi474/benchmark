# 取消会面、研讨会叫车与图书采购：接口与完整规格

按组织者与日期窗口取消会面并生成通知，按lead_minutes计算研讨会接送时刻，再按关键词、语言、预算及评分价格规则选择图书；本地子集不按装帧筛选。

## 环境与实现范围

Python 3.11及以上，仅标准库；本地合成输入，无GPU、训练、网络、真实账号或实时等待。所有时间按本题显式规则处理，禁止读取当前日期替代输入日期。

engines/分别实现算法内核，输入/输出文件接口表达算法之间真实依赖。

组件实现model.py、transform.py、render.py，以及根run_all.py和final_report.py；可新增私有辅助模块。未提供的实现文件需要自行创建。

README.md、TASK.md、inputs/、contract.json、check_module.py、check.py、integrate.py以及适用的materialize.py、__init__.py、parser.py不可修改。初始输入和契约为任务规格，不是可以修正的错误数据。

## 稳定接口与通用边界

- model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。

- transform.transform(payloads:list,contract:dict)：payloads按contract.inputs顺序，数量必须一致。返回恰好{"name":contract["name"],"result":算法结果对象}；本说明中的输出均指result，不额外套一层封装。

- 当输入对象键恰为name/result时，仅其result为业务输入；其他对象原样解释。不修改payloads/contract（包括嵌套值），不硬编码公开输入或上游结果。

- render.build_component(root:Path,contract_path:Path)：从给定root读取所有输入，调用transform并返回封装。执行python3 <组件目录>/render.py时，将封装写入contract.output；必须支持任意当前目录。缺文件或子命令失败须失败。

- context包另外保留<package>.parser.parse(payloads,contract)，返回与transform完全一致的封装。不要修改稳定parser来绕过实现。

- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。业务实际使用字段必须满足声明的类型、范围及有限数要求。未使用的额外字段可忽略；直接API输入中此类附加字段的递归非有限数拒绝仅为可选稳健性能力，不属于核心完成要求。文件加载器仍须拒绝非标准JSON数值，输出仍须为有限JSON。所有合法空集/无解按照各operation输出。

- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。

- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。

## 各组件业务规则

### engines/cancellations

operation：`meeting_cancel_plan`。输入文件及顺序见`engines/cancellations/contract.json`，输出为`outputs/cancellations.json`。

输入含events:[{id,start:int,end:int,kind:str,organizer:str,attendees:[id]}],window:[lo,hi],cancel_organizer:str。半开按活动start落入窗口且organizer匹配且kind="meeting"筛选；end>start。返回{cancelled:[id排序],notify:[{event_id,recipients:该活动去重排序参会人}]}。研讨会不因时间/组织者匹配而取消。

局部检查：`python3 engines/cancellations/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/ride

operation：`seminar_ride`。输入文件及顺序见`engines/ride/contract.json`，输出为`outputs/ride.json`。

输入含events同meeting_cancel_plan、seminar_id、lead_minutes:int>=0。seminar_id必须对应kind="seminar"，返回{event_id,pickup:该start-lead_minutes,destination:输入destination非空str}；时间允许负数（固定纪元分钟）。不依赖取消列表，不误选最近普通会议。

局部检查：`python3 engines/ride/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/books

operation：`book_purchase`。输入文件及顺序见`engines/books/contract.json`，输出为`outputs/books.json`。

输入含books:[{id,title,language,price_cents:int>=0,rating:int>=0}],book_query:{keyword,language,max_price_cents:int>=0}。title按casefold子串，语言精确匹配，价格<=上限；选rating最高、价格最低、id最小。返回{book_id:str或null,price_cents:int或null}，空候选不购买。本地输入不含装帧字段，本地改编不保留上游原题的精装筛选要求，不从title或id推断装帧。

局部检查：`python3 engines/books/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'取消会面、研讨会叫车与图书采购'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

