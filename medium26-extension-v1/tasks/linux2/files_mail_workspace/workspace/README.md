# 下载目录归档、邮件清理与目标回复：接口与完整规格

把 Downloads 下 PNG 归档到新子目录，独立清理本月特定主题邮件，再独立定位社媒经理来信并回复。

## 环境与实现范围

Python 3.11及以上，仅标准库；本地合成输入，无GPU、训练、网络、真实账号或实时等待。所有时间按本题显式规则处理，禁止读取当前日期替代输入日期。

初始仅README.md、check.py、integrate.py、materialize.py四个文件；物化后出现inputs/及products/，保留产品实现。linux指原仓库组织风格，不要求root或Linux系统。

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

### products/files

operation：`download_archive`。输入文件及顺序见`products/files/contract.json`，输出为`outputs/files.json`。

输入含files:[{path,hex}],download_prefix:str,archive_prefix:str,extensions:{扩展名含点:子目录名}。只处理download_prefix直接子文件，扩展名大小写不敏感，按extensions选择归档子目录，目标archive_prefix/子目录/原basename。未匹配/深层文件保留；目标已存在报错。返回{moves:[{from,to}]}按from，安全路径规则同公共规范。

局部检查：`python3 products/files/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/mail

operation：`mail_trash`。输入文件及顺序见`products/mail/contract.json`，输出为`outputs/mail.json`。

输入含emails:[{id,date:YYYY-MM-DD,subject:str,folder:str,sender:str,thread_id:str}],month:YYYY-MM,trash_keyword:str。选择日期属于month且subject按casefold子串命中且folder!="TRASH"，返回{trash_ids:排序ID}；日期必须合法，不匹配邮件保持原状。

局部检查：`python3 products/mail/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/reply

operation：`manager_reply`。输入文件及顺序见`products/reply/contract.json`，输出为`outputs/reply.json`。

输入含emails同mail_trash、reply_email_id、manager、reply_text。目标必须存在且sender==manager；直接按目标ID回复，不按主题挑最新邮件。返回{email_id,thread_id,to:manager,text:reply_text}，reply_text可为空串。

局部检查：`python3 products/reply/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/commit

operation：`workspace_commit`。输入文件及顺序见`products/commit/contract.json`，输出为`outputs/commit.json`。

输入依次原快照、download_archive、mail_trash、manager_reply。若目标回复邮件也在本批trash_ids，报ValueError（提交前冲突）。按moves重放文件迁移，按trash_ids将对应邮件folder设TRASH，输出{files:[{path,hex}]按path,emails:按id,reply:上游回复}；禁止触碰其他文件/邮件。

局部检查：`python3 products/commit/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'下载目录归档、邮件清理与目标回复'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

先运行python3 materialize.py。受保护脚本验证内嵌清单哈希，生成输入、产品契约、检查及实现占位；重复执行保留已有实现，并验证生成的受保护文件。不得修改物化器或其生成的输入/契约/检查。此处文件操作基于本地快照，禁止操作真实home或账号。

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

