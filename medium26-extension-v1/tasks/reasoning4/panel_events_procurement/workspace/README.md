# 两场座谈会、群邀请与物资采购：接口与完整规格

计算首次可用三小时时段和下月第二个周日的活动，寻找指定主题/活跃日期的群聊，另外选择可用最贵物资；活动建立后通知目标群。

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

### engines/calendar

operation：`panel_slots`。输入文件及顺序见`engines/calendar/contract.json`，输出为`outputs/calendar.json`。

输入{now:int,windows:[{id,start:int,end:int}],busy:[{id,start:int,end:int}],duration:int>=1,gap:int>=0,...}，单位分钟，所有区间半开且end>start。从windows并集减去busy并排除now前时间，贪心选最早可容纳duration的首场，再选start>=首场end+gap的最早第二场，两个窗口相接可视为连续。返回{slots:[{start,end}],complete:是否两场}，最多2场。合法无足够时段返回部分结果，不报错。

局部检查：`python3 engines/calendar/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/invitees

operation：`panel_invitees`。输入文件及顺序见`engines/invitees/contract.json`，输出为`outputs/invitees.json`。

输入含groups:[{id,members:[非空id]}],invite_groups:[群ID],exclude:[联系人ID]。所选群必须存在，成员集合并集减exclude，返回{members:排序ID,group_id:输入namespace+"-panel"}；namespace非空。允许重复的群引用和成员，未知群报错。

局部检查：`python3 engines/invitees/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/supplies

operation：`supply_selection`。输入文件及顺序见`engines/supplies/contract.json`，输出为`outputs/supplies.json`。

输入含products:[{id,category,stock:int>=0,price_cents:int>=0,rating:int>=0}],requirements:[{category,quantity:int>=1}]。每个category仅一条需求，按库存足够筛选，选择rating最大、price_cents最小、id最小商品。返回{items:[{category,id,quantity,total_cents}],unavailable:[category排序]}，items按category。不以售价最大代替评分，不跨商品拼库存。

局部检查：`python3 engines/supplies/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/commit

operation：`panel_commit`。输入文件及顺序见`engines/commit/contract.json`，输出为`outputs/commit.json`。

输入依次为panel_slots、panel_invitees、supply_selection。返回{events:[{id,start,end,members}],notification:null或{group_id,members,event_ids},purchase:物资选择结果}。只有complete=true才生成两场，ID为group_id+"-1"/"-2"；通知引用两场ID，成员读取上游members。无两场时events=[]、notification=null，仍保留独立采购结果。

局部检查：`python3 engines/commit/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'两场座谈会、群邀请与物资采购'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

