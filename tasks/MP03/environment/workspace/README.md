# 三种挂载格式的离线事实归并：接口与完整规格

分别解析三类挂载快照，归一为统一记录，再按固定来源优先级归并并生成冲突与筛选结果。

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

### domains/fstab

operation：`fstab_parse`。输入文件及顺序见`domains/fstab/contract.json`，输出为`outputs/fstab.json`。

输入含fstab:str。逐行去首尾空白，忽略空行和#开头注释；其他行按空白切成4到6列，前4列为device,mount,fstype,options。字段中的\040、\011、\134分别解为空格、tab、反斜线。返回 {records:[{device,mount,fstype,options:逗号分割去重排序}]}，保持行序；不读取真实系统。

局部检查：`python3 domains/fstab/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/aix

operation：`aix_parse`。输入文件及顺序见`domains/aix/contract.json`，输出为`outputs/aix.json`。

输入含aix:str。忽略空行/#注释；以非缩进的“挂载点:”开始段落，段内key=value可含空白。只支持dev、vfs、options，未知或重复key报错。dev必需，vfs缺省jfs2，options缺省rw；段头为mount。输出同fstab_parse，保持段序；无段头属性/缺设备报ValueError。

局部检查：`python3 domains/aix/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### domains/mount

operation：`mount_parse`。输入文件及顺序见`domains/mount/contract.json`，输出为`outputs/mount.json`。

输入含mount:str。固定Linux语法“device on mountpoint type fstype (option1,option2)”；一条记录一行，空行忽略。device/mountpoint可含\040但不含裸空白，fstype无空白，括号内不能为空。输出同fstab_parse；不支持其他OS的自由格式。

局部检查：`python3 domains/mount/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/merged

operation：`mount_merge`。输入文件及顺序见`views/merged/contract.json`，输出为`outputs/merged.json`。

输入依次为fstab、aix、mount解析结果。按此固定来源优先级、再原记录行序为每个mount选首条；返回 {records:按mount排序并增加source的胜出记录,conflicts:[{mount,evidence:[增加source的全部记录]}]}。同点只要device/fstype/options任一不同即冲突，证据包含相同的重复记录；完全相同则不报冲突。

局部检查：`python3 views/merged/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'三种挂载格式的离线事实归并'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

