**运行时 multi-agent 专项审计**

统计范围为七臂矩阵各56个选定attempt，共392题位。包含无效提交、预算截断和证据失败；LATTE四次独立补跑不进入本表分母。运行机制和任务质量分别核算。

| Harness | 实际运行证据 | 并行证据 |
|---|---|---|
| ROMA | 56/56有递归子Solve和递归子规划 | 52/56有叶Executor活动窗口重叠；39/56有工具执行重叠 |
| LATTE planning-adapted | 39/56有非Lead teammate实际返回模型回答；38/56有多个teammate回答 | 36/56有teammate模型回合重叠，峰值3；已计时run_script/run_tests未见跨teammate工具重叠 |
| LangGraph | 56/56有worker模型响应；52题4个worker，4题3个worker | 27/56有worker执行窗口重叠，峰值3 |
| Codex | 1/56出现3个实际子线程，均completed；父接收并进入后续模型请求各3份结果 | 工具执行并行未知 |
| Nanobot | 本轮选定56题未观察到子Agent运行 | 本轮未观察到 |
| OpenCode | 本轮选定56题未观察到子Agent运行 | 本轮未观察到 |
| DSH | 本轮选定56题未观察到子Agent运行 | 本轮未观察到 |

LATTE执行阶段的动态任务展开出现在12/56题，共28次accepted discover_task。筛选条件为round>0且提出者非System，系统自动注入的fix任务不计入。例如incident_pipeline_repair执行阶段新增1个模型任务，supply_chain_assurance新增5个，后者保留100轮部分评分标签。

LATTE的agent_turn区间包围reply_async模型调用，使用原生span_id配对，同进程ts时间计算不同teammate区间交叠。工具统计只覆盖有原生计时的同步subprocess run_script/run_tests。回合并行、HTTP并发和工具执行并行分别记录。teammate数量由运行配置预先给定。

ROMA统计递归子求解实例，复用已有Agent定义，runtime_created_agent_definitions的观测最大值为0。叶活动窗口峰值8、工具并行峰值3，上游HTTP门禁为4。活动窗口含等待时间，叶并发宽度与实际上游HTTP宽度分别保留。

LangGraph属于本轮planner/worker编排变体。worker有独立身份、模型响应及生命周期。原始agent.run起止事件的span_id不同，审计按唯一agent_id+node_id配对并使用monotonic_ns计时；autonomous_delegation沿用源监控false。

Codex正例为original/linux_release_analysis。model_tool_spawn_observed=true，3个子线程终态均completed。父收到结果并纳入后续模型请求已有各3条证据，发送端显式事件缺测。模型自主性字段仍为unknown，本例reward0/1与运行触发分开记录。

矩阵之外，AOrchestra的独立MP17 R2 pilot也记录3次delegation.created、3次delegation.completed，最大并发子Agent为1。该pilot仅作单列运行正例，未计入七臂56题分母。来源审计文件SHA256和定位符存于JSON。

- [逐题计数、来源事件SHA256与方法](runtime-multiagent-audit.json)
- [可复算的离线审计脚本](scripts/audit_runtime_multiagent.py)

持有原始outputs目录时，可用脚本的outputs-root、release-root和output三个参数重算。发布的JSON提供可移植来源定位符及指纹，提供汇总和计数，不包含原始提示、工具输出或LATTE源码。
