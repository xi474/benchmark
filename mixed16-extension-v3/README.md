# Mixed16 extension v3

16 个独立任务保留原名，按已有四种目录风格各分4个。v3针对API下线、身份联邦、搜索索引和Linux组4项增加算法与真实结果依赖；其余9项保持v2任务文件逐字节一致。原仓库18个条目未修改。输入规模用于正确性与组合优化，不宣称是更重的性能压力题。

## 四类结构

- multistage4：domains/ + views/，3 个证据领域 + 3 个视图；版本去重、风险排序、负载平衡、条件修复与关键路径。
- reasoning4：engines/，3个算法引擎；API新增带预算/期限的集合覆盖，以及公告释放时间、人员互斥、全局资源容量共同约束的精确调度。
- context8：3个可导入package，保留parser接口；身份联邦新增轮换、祖先撤销传播和循环组继承闭包；搜索新增字段重命名图、分片墓碑恢复和预算仲裁优化。
- linux2：初始仍只有README.md、check.py、integrate.py、materialize.py，物化后3个产品。每项改为两个产品并行、第三个消费二者结果：最宽信任路径与轮换覆盖、备份链与原子事务恢复、法律保留分组背包与日志授权、ECMP与有状态防火墙实际路径核验。linux指原仓库结构风格，标准库验证也支持Windows。

统一 TASK.md、README 章节、契约字段顺序、接口名字与验证流程。核心组件数为3或6，不再统一为8个同构组件。静态夹具含24–55条证据/事件、30个span、40条请求等，并非性能基准；隐藏测试另覆盖空集、非法字段、重复ID/修订冲突、非有限数、分数截断、默认拒绝、偏移缺口及集成冲突。

## 给被测代理的内容

每次仅给 tasks/<suite>/<name>/TASK.md 和对应 workspace/。绝不能挂载本数据集根目录、_authoring/、verifier/ 或旧版备份。契约含输入文件接口，目标是从代码与文件接口发现当前可执行机会，不声称隐藏所有依赖；不提供任务计划DAG、预先标注波次、并行标签或计时策略。算法输入中的业务依赖图是待求解数据，不是评测调度DAG。

## 验收与信任边界

代理在工作区运行 python3 check.py 做本地冒烟验证，没有完整golden。正式评分从可信只读评测器执行：

    python3 verifier/verify.py --entry multistage4/regional_failover_readiness --workspace <candidate-workspace>

外部 verifier 在运行前后校验可信 protected_hashes.json，覆盖 check.py 自身、输入、契约、局部检查和已有集成脚本；linux额外核验物化文件。随后从作者参考算法计算预期、比较全部输出，并用未下发的变更夹具直接调用组件API。缺失实现、篡改检查器、错误输出及只硬编码公开夹具不能获得通过。

这要求 harness 将 verifier/、_authoring/ 置于代理不可读取且不可写入的位置；仅靠在同一可写磁盘保存哈希不是安全沙箱。作者参考实现与测试输入不在workspace内，分发时也应隔离；外部verifier不是恶意Python的进程隔离器。

## 作者工具

_authoring/含任务规格、参考算法和构建/QA脚本；verifier/含独立评分入口、API探针与可信哈希。python3 _authoring/qa.py --root . 重跑参考实现、初始失败、算法捷径及上游结果忽略负例，输出validation_report.json、structure_audit.json、duplicate_audit.json。查重同时比较提示、工作区、完整输入包，以及忽略任务/组件命名后的算法依赖图；共享基础算法或单个夹具不等于任务级重复。正式评测不会填充代理工作区。

本包SHA256SUMS覆盖除其自身及__pycache__之外的分发文件。manifest.workspace_tree_sha256：按相对路径排序，拼接 path+NUL+文件sha256+LF，对UTF-8字节计算SHA-256。原仓库的manifest不合并或篡改；此扩充包独立记录16条目。

## 组件执行 DAG 图集

[查看全部16个任务的DAG图](_authoring/dags/README.md)。每项提供SVG、PNG、Mermaid源码、完整边表和契约摘要；主图采用执行DAG传递约简，完整直接读取边保留在Mermaid/JSON中。

图集仅用于作者分析，位于`_authoring/`，不得向被测代理提供或与workspace一起挂载。分层与宽度是静态依赖指标，不是实测耗时或加速比。
