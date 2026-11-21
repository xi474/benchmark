# 文本、内联内容和文件的 multipart 组装：接口与完整规格

把文本字段、内联内容和文件内容编码为一致的 multipart 请求体，并返回匹配的 Content-Type/boundary。

## 环境与实现范围

Python 3.11及以上，仅标准库；本地合成输入，无GPU、训练、网络、真实账号或实时等待。所有时间按本题显式规则处理，禁止读取当前日期替代输入日期。

独立可导入package保留parser.parse(payloads,contract)稳定接口，修复包内实现及跨包兼容。

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

### parts

operation：`multipart_parts`。输入文件及顺序见`parts/contract.json`，输出为`outputs/parts.json`。

输入{fields:object,files:{安全相对路径:字节hex},boundary:仅字母数字短横线非空str}。字段名只允许[A-Za-z0-9_.-]+。字段值为str，或含filename/content/mimetype的非空对象；content若存在必须str且优先于filename文件读取。纯str为text/plain，无文件名；对象content为inline，filename存在则取basename；仅filename则从files读取并base64编码。显式mimetype优先；否则filename后缀.txt/.json/.jpg映射text/plain/application/json/image/jpeg，其余application/octet-stream（无filename inline同此）。返回{parts:[{name,filename:str或null,mimetype,encoding:raw/base64,hex}]}按name排序。文件名只允许安全路径的basename字符[A-Za-z0-9_.-]+，MIME符合token/token；缺文件或空子对象ValueError。

局部检查：`python3 parts/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### encoding

operation：`multipart_encoding`。输入文件及顺序见`encoding/contract.json`，输出为`outputs/encoding.json`。

输入为multipart_parts。raw部件保留原字节；base64部件对字节编码并每76个ASCII字符折行，行间CRLF，无额外末尾CRLF。返回{parts:[在每个部件原字段外增加payload_hex]}，保留顺序，未知encoding报错。

局部检查：`python3 encoding/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### body

operation：`multipart_body`。输入文件及顺序见`body/contract.json`，输出为`outputs/body.json`。

输入依次原快照、multipart_encoding。boundary仅[A-Za-z0-9-]+，若字节串出现在任一payload报ValueError。每part写"--boundary\r\n"，文件base64时先写"Content-Transfer-Encoding: base64\r\n"，再Content-Type行，再Content-Disposition行，其格式为form-data; name="字段名"并可附; filename="文件名"，随后CRLF空行、载荷、CRLF；最后"--boundary--\r\n"。返回{content_type:"multipart/form-data; boundary=...",body_hex}。不启动HTTP或使用私有随机boundary。

局部检查：`python3 body/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'文本、内联内容和文件的 multipart 组装'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

