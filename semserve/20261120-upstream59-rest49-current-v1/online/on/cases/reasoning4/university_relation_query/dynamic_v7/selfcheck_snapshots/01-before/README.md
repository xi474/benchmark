# 大学任职、在读人数与国家集合查询：接口与完整规格

在输入已预筛为正式教授的名单中，按EU任职及至少一个单独任职部门在读人数超过10的条件查询，并返回全部任职国家。

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

- 必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数，布尔字段必须bool；无明示默认值不自行补默认。业务实际使用字段必须满足声明的类型、范围及有限数要求。未使用的额外字段可忽略；直接API输入中此类附加字段的递归非有限数拒绝仅为可选稳健性能力，不属于核心完成要求。文件加载器仍须拒绝非标准JSON数值，输出仍须为有限JSON。所有合法空集/无解按照各operation输出。

- 字符串排序按Python通常字典序；非空字符串要求strip后非空，但除规则明示外保留原内容。安全相对路径使用/，禁止绝对路径、反斜线、冒号、空段、.和..。hex按bytes.fromhex解释，不将hex文本当字节计算摘要。

- 数值计算比较容差为相对/绝对1e-9；非数值结构、键集合、列表顺序、文本/字节格式必须精确。输入中的算法图是业务数据，不是Agent执行计划。

## 各组件业务规则

### engines/eu

operation：`eu_professors`。输入文件及顺序见`engines/eu/contract.json`，输出为`outputs/eu.json`。

输入{departments:[{id,country}],professors:[{id,departments:[部门ID]}],students:[{id,enrolments:[{department,start:ISO日期,end:ISO日期或null}]}],as_of:ISO日期,eu:[国家代码]}。教授部门引用存在，重复任职引用按集合。只要至少一个任职部门country在给定eu中即合格；返回{ids:[合格教授ID排序]}。EU口径不从系统时钟或网络推断。professors是数据准备阶段已预筛为正式教授的名单；本API不接收混合职称候选、不实现职称筛选，也不从id推断职称。其余三个组件继承此输入范围。

局部检查：`python3 engines/eu/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/students

operation：`department_students`。输入文件及顺序见`engines/students/contract.json`，输出为`outputs/students.json`。

输入同eu_professors。start<=as_of且(end=null或as_of<end)才为在读，end非null时须>start；逐department以student.id做DISTINCT，重复入学记录不多计。同一学生在多个部门可分别计数，不能先跨部门并集。返回{counts:{全部部门ID:在读人数}}。日期以YYYY-MM-DD固定，不含时区。

局部检查：`python3 engines/students/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/countries

operation：`employment_countries`。输入文件及顺序见`engines/countries/contract.json`，输出为`outputs/countries.json`。

输入同eu_professors。返回{countries:{教授ID:全部任职国家去重排序}}，包括EU之外任职，不只返回使教授合格的国家。教授无任职返回空列表。

局部检查：`python3 engines/countries/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

### engines/query

operation：`university_query`。输入文件及顺序见`engines/query/contract.json`，输出为`outputs/query.json`。

输入依次原输入、eu_professors、department_students、employment_countries。仅返回EU资格合格且至少一个单独任职部门在读人数>10的教授；达到人数部门可不同于EU资格部门。返回{professors:[{id,countries:全部任职国家,eligible_departments:[人数>10部门排序]}]}按id。两个部门各6人不等同于某部门>10。

局部检查：`python3 engines/query/check_module.py`；先生成该契约所需输入及本组件输出，不跳过缺失依赖。

## 集成、JSON与最终报告

所有JSON产物按UTF8、ensure_ascii=False、sort_keys=True、indent=2、allow_nan=False写出，末尾一个真实换行。数值容差不允许省略字段、额外封装或改写字符串。

实现run_all.py，定位工作区并依据文件接口执行全部必要组件。每次调用应重新计算全部组件输出，不借用旧outputs；缺失依赖、环或子命令失败必须非零退出。已有python3 integrate.py读取所有组件产物，写outputs/core_manifest.json={"components":{组件名:result}}，不得修改集成器。

实现final_report.py，读取完整core对象，写outputs/final_report.json，恰含title、component_count、sha256、attention。title准确为'大学任职、在读人数与国家集合查询'，component_count为components键数。

sha256针对完整core对象（含外层components），序列化为json.dumps(core,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")，无末尾换行，再求SHA256小写hex。

attention为满足任一条件的组件名去重排序列表：result.blocked显式true；complete/checkout/committed/ok任一显式false；unavailable/missing/conflicts/unreachable任一非空。不存在字段不触发；false与0/null不混同。

## 运行与验收

在工作区运行python3 check.py。该命令清理outputs、执行适用的物化、运行run_all、检查结构和局部接口；公开冒烟不包含全部金标，也不决定正式得分。外部可信verifier检查受保护文件、所有产物、不同输入的API探针、load_payload和build_component。

Agent输入只有本题TASK.md与workspace。作者参考解、来源评审、DAG、隐藏向量、seal和正式验证器均保留在工作区外，不能作为被测Agent上下文。

