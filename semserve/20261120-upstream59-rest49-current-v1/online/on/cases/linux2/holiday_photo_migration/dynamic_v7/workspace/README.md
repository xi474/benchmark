# 节日照片迁移后发送与缺失报告：接口与完整规格

处理已限定目标年份并附节日标注的照片元数据，按所需节日分类、迁移，再用新路径生成发送清单和缺失报告；本地子集不解析年份、不执行独立清理。

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

- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。业务实际使用字段必须满足声明的类型、范围及有限数要求。未使用的额外字段可忽略；直接API输入中此类附加字段的递归非有限数拒绝仅为可选稳健性能力，不属于核心完成要求。文件加载器仍须拒绝非标准JSON数值，输出仍须为有限JSON。所有合法空集/无解按照各operation输出。

- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。

- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。

## 各组件业务规则

### products/classify

operation：`photo_classification`。输入文件及顺序见`products/classify/contract.json`，输出为`outputs/classify.json`。

输入{files:[{path,hex}],photos:[{path,festival}],festivals:[唯一非空str],destination:安全相对目录,recipient:非空str}。photos路径唯一且在files内，每张festival非空。仅选择festival在festivals内的照片，按(festival,path)排序。返回{selected:[{path,festival}],missing:[没有照片的festival排序]}；同一节日可有多张，不能找到一张就停止扫描。输入photos是数据准备阶段已限定为同一目标年份并完成节日标注的元数据；年份不是本API字段，不从path推断年份或节日，不读取系统日期。files可含其他未选文件；本地子集不执行独立照片清理。

局部检查：`python3 products/classify/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/migrate

operation：`photo_migration`。输入文件及顺序见`products/migrate/contract.json`，输出为`outputs/migrate.json`。

输入依次为原照片快照、photo_classification。将selected源路径移动到destination/原路径（保留子路径避免同名覆盖）；目标已存在报ValueError；未选文件不动。返回{moves:[{from,to,festival}],files:[{path,hex}]}，moves按(from,to)、files按path。没有照片不失败；hex字节必须保持不变。

局部检查：`python3 products/migrate/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### products/outbox

operation：`photo_outbox`。输入文件及顺序见`products/outbox/contract.json`，输出为`outputs/outbox.json`。

输入依次为原快照、photo_classification、photo_migration。输出{to:recipient,attachments:[迁移后路径排序],missing:分类结果missing,message:str}。message无缺失时为"Photos ready"，有缺失为"Missing: "+以", "连接的missing。必须从迁移结果选附件，不引用旧路径；空附件也生成缺失报告。attachments包含本地子集中全部已迁移照片，而非只选上游原题的某个节日；本任务不另做女儿身份搜索或清理其他照片。

局部检查：`python3 products/outbox/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'节日照片迁移后发送与缺失报告'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

先运行python3 materialize.py。受保护脚本验证内嵌清单哈希，生成输入、产品契约、检查及实现占位；重复执行保留已有实现，并验证生成的受保护文件。不得修改物化器或其生成的输入/契约/检查。此处文件操作基于本地快照，禁止操作真实home或账号。

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

