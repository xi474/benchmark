# 每日晚餐提醒的去重、冲突取消与通知：接口与完整规格

生成至下周五的19点晚餐提醒；已有符合条件晚餐的日期保持不变，其他日期处理冲突并通知受影响参会人。

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

- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。未知额外字段可忽略，但其中非有限JSON仍非法。所有合法空集/无解按照各operation输出。

- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。

- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。

## 各组件业务规则

### engines/dates

operation：`dinner_days`。输入文件及顺序见`engines/dates/contract.json`，输出为`outputs/dates.json`。

输入{today:YYYY-MM-DD,events:[{id,start:YYYY-MM-DDTHH:MM,end:同格式,kind:str,attendees:[id]}],contacts:[id]}。日期从today到下一自然周周五（周一为周首），两端包含；例如2026-11-04到2026-11-13。返回{dates:[YYYY-MM-DD按升序]}，固定时区、不等待、不处理RRULE。

局部检查：`python3 engines/dates/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/calendar

operation：`dinner_calendar_index`。输入文件及顺序见`engines/calendar/contract.json`，输出为`outputs/calendar.json`。

输入同dinner_days。事件ID唯一，end>start，所有参会人存在于contacts（contacts不重复），kind非空。本地子集将19:00开始的kind=dinner事件限制为当天20:00前结束（含20:00），其他活动可跨日。返回{events:[原事件按id,attendees去重排序],existing_dinners:[start时间恰19:00且kind="dinner"的日期去重排序]}。旧晚餐哪怕只持续10分钟也跳过该日的新增/冲突选择。所有时间须无时区且精确到分钟。

局部检查：`python3 engines/calendar/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/plan

operation：`dinner_change_plan`。输入文件及顺序见`engines/plan/contract.json`，输出为`outputs/plan.json`。

输入依次dinner_days、dinner_calendar_index。跳过existing_dinners内日期的新增与冲突选择；其他日创建19:00–20:00晚餐提醒，ID="dinner-日期"，kind=dinner,attendees=[]。取消所有与新提醒半开区间相交旧事件，跨日旧事件只取消一次：即使覆盖了跳过日，只要也与未跳过日的新提醒冲突，仍整条取消。恰19点结束不冲突。新ID与任何旧事件冲突报错。返回{added:[新事件按start],cancelled:[原事件ID排序],snapshots:[被取消原事件按id]}。

局部检查：`python3 engines/plan/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/notifications

operation：`dinner_notifications`。输入文件及顺序见`engines/notifications/contract.json`，输出为`outputs/notifications.json`。

输入为dinner_change_plan。从被取消事件快照为每位受影响联系人生成一条通知，返回{outbox:[{to:联系人ID,event_ids:[该人被取消活动ID去重排序]}]}按to；无参会人不发通知。不通知保留活动参会人，不因跨日活动产生重复。

局部检查：`python3 engines/notifications/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/apply

operation：`dinner_apply`。输入文件及顺序见`engines/apply/contract.json`，输出为`outputs/apply.json`。

输入依次dinner_calendar_index、dinner_change_plan、dinner_notifications。将cancelled从旧events删除，再加入added，输出{events:[最终事件按id],outbox:上游通知}。未涉及旧事件原样保留；重复运行同today和新events应无新增/取消/通知，这是有限状态幂等，不是真实日历调用。

局部检查：`python3 engines/apply/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'每日晚餐提醒的去重、冲突取消与通知'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

