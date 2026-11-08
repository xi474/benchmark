# 取消日程后多渠道通知：接口与完整规格

从初始日历快照确定需取消的上午社交活动，取消后通过邮件、新群消息和回退渠道通知。

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

### domains/calendar

operation：`cancel_morning`。输入文件及顺序见`domains/calendar/contract.json`，输出为`outputs/calendar.json`。

输入{events:[{id,start:int,end:int,social:bool,cancelled:bool,attendees:[contact_id]}],day:int>=0,contacts:[{id,email:str或null,message:str或null,chat:str或null}]}；时间为分钟。选择start在[day*1440,day*1440+720)且social且未cancelled的活动，end>start。返回{cancelled:目标id排序,snapshots:目标原记录按id,remaining:其余原记录按id}。不删除已经取消的旧记录。

局部检查：`python3 domains/calendar/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/channels

operation：`channel_directory`。输入文件及顺序见`domains/channels/contract.json`，输出为`outputs/channels.json`。

输入同cancel_morning。联系人ID唯一，email/message/chat必须为null或非空str。每人首选message，其次chat；email独立可用。返回{contacts:{id:{email,primary:message/chat/null,address:所选地址或null}}}。不因目前没有目标活动而忽略联系人校验。

局部检查：`python3 domains/channels/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/notifications

operation：`cancel_notifications`。输入文件及顺序见`views/notifications/contract.json`，输出为`outputs/notifications.json`。

输入依次为cancel_morning结果、channel_directory结果。将目标快照参会人取并集、去重，未知ID报错。返回{outbox:[{channel,to,recipients,requires}],unreachable:[id],group:null或{ id:"cancelled-social",members,requires }}。requires为全部本批cancelled ID排序。每个可email者独立email；message首选者组成一个新群，group.members按id、outbox增加一条message_group（to为群ID，recipients为成员）；chat回退者各发一条chat。两渠道均无者进入unreachable。outbox按(channel,to)排序，非群recipients=[contact_id]。先取消再通知且群先创建由requires及group表达，不执行真实发送。

局部检查：`python3 views/notifications/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'取消日程后多渠道通知'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

