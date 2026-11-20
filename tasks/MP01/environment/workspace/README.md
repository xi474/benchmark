# 可关闭成员的硬/软加权投票：接口与完整规格

修复组合估计器的关闭成员、样本权重转发与投票对齐，同时要求硬投票和软投票都可使用。

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

### domains/fit

operation：`fit_members`。输入文件及顺序见`domains/fit/contract.json`，输出为`outputs/fit.json`。

输入 {classes:[唯一非空字符串],sample_weight:[非负数],members:[{id,active:bool,weight:非负数,predictions:[类别],classes:[类别],probabilities:[[概率]]}]}。sample_weight 长度为样本数。成员ID唯一；关闭成员仅校验id/active，不读取其余字段。返回 {classes,sample_count,members:[原活动成员的深拷贝并增加fit_weight:原sample_weight]}，保留输入成员顺序。活动成员至少一个且权重和>0；其predictions长度须等于样本数、标签属于全局类别，classes必须为全局类别的一个排列；概率矩阵尺寸一致、各项>=0且每行和距1不超过1e-9。不执行真实训练。

局部检查：`python3 domains/fit/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/hard

operation：`hard_vote`。输入文件及顺序见`views/hard/contract.json`，输出为`outputs/hard.json`。

唯一输入为fit_members的结果封装。逐样本按成员weight累加predictions的类别票数；平局按全局classes的先后次序。返回 {predictions:[类别],scores:[[按全局classes排列的未归一票数]]}。必须使用上游已筛选成员和权重，不读取固定训练样例。

局部检查：`python3 views/hard/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/soft

operation：`soft_vote`。输入文件及顺序见`views/soft/contract.json`，输出为`outputs/soft.json`。

唯一输入为fit_members结果。将各成员probabilities的列按该成员classes映射到全局classes，然后按weight加权平均。返回 {predictions,probabilities}，预测平局按全局classes顺序；不能假定各成员的概率列顺序相同。

局部检查：`python3 views/soft/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### views/comparison

operation：`vote_comparison`。输入文件及顺序见`views/comparison/contract.json`，输出为`outputs/comparison.json`。

输入依次为硬投票、软投票结果。样本数不一致报ValueError；返回 {hard:硬预测,soft:软预测,disagreements:[两路预测不同的样本下标]}。

局部检查：`python3 views/comparison/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'可关闭成员的硬/软加权投票'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

