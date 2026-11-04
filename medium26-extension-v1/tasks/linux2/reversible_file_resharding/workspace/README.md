# 受目录容量限制的可逆文件重分片：接口与完整规格

在每目录条目数、每文件字节数上限下重分片小型文件树，并能精确恢复原路径和原字节。

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

### products/chunks

operation：`reshard_chunks`。输入文件及顺序见`products/chunks/contract.json`，输出为`outputs/chunks.json`。

输入{files:[{path,hex}],max_file_bytes:int>=16,max_entries:int>=2}。原文件路径安全且唯一。按path排序，将每文件原字节顺序切成最多max_file_bytes的块；全球块编号从0起为d000000.bin（至少6位十进制）。空文件无块。返回{chunks:[{name,hex}],manifest:{files:[{path,size,sha256,parts:[块名按序]}]}}。保留空文件、空行、无末尾换行和任意字节，不做strip/压缩/最优装箱。

局部检查：`python3 products/chunks/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/layout

operation：`reshard_layout`。输入文件及顺序见`products/layout/contract.json`，输出为`outputs/layout.json`。

输入依次原输入、reshard_chunks。manifest紧凑规范JSON的UTF8字节也切成max_file_bytes大小，命名m000000.bin起，元数据同样受大小上限限制。数据块与元数据块按name字典序排序，共N项；取最小h>=1使max_entries**h>=N。每项序号i转成恰h位max_entries进制，前h-1位各作为目录n<数字>，末位不入路径，文件名仍原name。返回{tree:[{path,hex}]按path,max_entries,max_file_bytes}；这样每层直接目录项数（文件+子目录）均受限。索引不放在超大单独JSON文件，layout对象只是文件树快照。

局部检查：`python3 products/layout/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/restore

operation：`reshard_restore`。输入文件及顺序见`products/restore/contract.json`，输出为`outputs/restore.json`。

唯一输入为reshard_layout文件树。验证每文件<=max_file_bytes、每目录直接项（文件+子目录）<=max_entries、无文件/目录重名，路径安全且basename唯一。所有basename必须m数字.bin或d数字.bin，m块从000000连续编号，连接后解析manifest。按manifest.files顺序还原parts；原path唯一安全，每个d块须恰被引用一次，size和原字节sha256相符；缺块、重复引用、额外数据块或摘要不符报ValueError。返回{files:[{path,hex}]按path,total_bytes}。不读取原输入当作恢复答案。

局部检查：`python3 products/restore/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'受目录容量限制的可逆文件重分片'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

先运行python3 materialize.py。受保护脚本验证内嵌清单哈希，生成输入、产品契约、检查及实现占位；重复执行保留已有实现，并验证生成的受保护文件。不得修改物化器或其生成的输入/契约/检查。此处文件操作基于本地快照，禁止操作真实home或账号。

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

