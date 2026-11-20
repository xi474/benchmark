# 附件发送后归档与独立清理：接口与完整规格

定位新闻附件、匹配两位收件人并发送；双人成功后归档，同时独立处理家庭目录清理与统计。

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

### products/receipts

operation：`attachment_receipts`。输入文件及顺序见`products/receipts/contract.json`，输出为`outputs/receipts.json`。

输入{files:[{path:安全相对POSIX路径,hex:原字节十六进制}],attachments:[路径],recipients:[唯一非空id],send_ok:{recipient_id:bool},cleanup_prefix:str,archive_prefix:str}。附件去重排序且必须存在；recipients不重复。返回{attachments:[{path,sha256:原始字节摘要}],receipts:[{recipient,ok}]}，收件人按id排序，ok读取send_ok对应布尔值；不能以“尝试发送”当成功。

局部检查：`python3 products/receipts/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/cleanup

operation：`independent_cleanup`。输入文件及顺序见`products/cleanup/contract.json`，输出为`outputs/cleanup.json`。

输入同attachment_receipts。cleanup_prefix为安全目录名，不含尾斜线。选择该目录下所有以.tmp结尾的普通文件，返回{delete:[排序路径]}。按路径段边界匹配，home/tmp不应匹配home/tmp-old；不操作附件或归档。

局部检查：`python3 products/cleanup/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/archive

operation：`archive_after_send`。输入文件及顺序见`products/archive/contract.json`，输出为`outputs/archive.json`。

输入依次为原快照、attachment_receipts、independent_cleanup。archive_prefix为安全相对目录。仅所有receipts.ok都为true且至少一位收件人时，按附件原完整路径拼到archive_prefix/下移动；其他情况完全不移动附件。清理delete始终可执行。任何重复目标、目标已存在、清理与移动源重叠均ValueError。输出{moves:[{from,to}],deleted:[path],blocked:bool,files:[{path,hex}]}，moves按from、files按path，字节不变。这是本地状态重放，不发邮件、不改真实home。

局部检查：`python3 products/archive/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'附件发送后归档与独立清理'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

先运行python3 materialize.py。受保护脚本验证内嵌清单哈希，生成输入、产品契约、检查及实现占位；重复执行保留已有实现，并验证生成的受保护文件。不得修改物化器或其生成的输入/契约/检查。此处文件操作基于本地快照，禁止操作真实home或账号。

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

