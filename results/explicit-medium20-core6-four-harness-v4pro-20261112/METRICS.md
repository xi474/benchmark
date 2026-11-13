# 指标字段与来源

所有CSV采用UTF-8 BOM；布尔为True/False，空字符串表示未知或不适用，不能按0解析。各字段范围以逐格覆盖率为准。

## 质量和身份

`arm/harness/dataset/task_id`确定逻辑题位，`trial_id`确定选定attempt。`score_status/scored`只描述Harbor评分存在且完整性通过；`terminal_label_original`保留原标签，`terminal_label_audited`追加异常旁注，不能覆盖前者。`reward/max_reward`沿用原score政策；`core_pass/core_total`和`api_pass/api_total`分别是核心及其API子集，`api_accuracy=api_pass/api_total`。optional稳健性不混入API。`score_policy_version`、result/score SHA及相对source refs保留出处。

## 时钟和资源

`harbor_started_at/harbor_finished_at`来自Harbor原始result，`harbor_e2e_sec`是两者差。`agent_execution_sec/verifier_sec`来自原生阶段起止。队列等待不在E2E内；没有统一恢复安装阶段的独立纯耗时，不用差值冒充。

`model_http_duration_sum_sec`是逐已结算请求上游elapsed之和；`model_http_duration_known_requests`及`settled_requests`标明覆盖。此值不排除供应商排队/网络，不是纯GPU时间。父子并行时和可能超过E2E。缺项时只有known_lower_bound可用。

`resource_samples/resource_window_sec`来自原task-container cgroup采样；`sampled_peak_memory_bytes`取采样内存最大值，`sampled_cpu_time_sec`取可比CPU累计值最后减最初。采样不足/计数回退保留未知。`per_agent_resource_status=not-instrumented-by-design`，不是零资源。

`tool_calls`为规范化原生工具span数，可能包括编排，不保证每项成功或实际启动进程。`tool_complete_timed_spans`标明起止覆盖；`tool_span_union_sec`只在全部span起止可用且同一clock_scope时给值；`tool_span_known_lower_bound_sec`不完整时只是已知下界。`tool_span_timing_basis`指明native monotonic/unix来源，不能用接收日志时间替代。

`tool_span_peak_including_orchestration`包含Task/spawn/wait。`tool_leaf_span_peak`排除已识别编排名，仍只是工具事件重叠。`actual_os_process_parallelism=not-uniformly-instrumented`。Codex的`native_linked_process_records`为关联记录数，`native_process_complete_duration_records`为完整时长证据数；`native_reported_wall_chunks_sec`仅输出片段墙钟总和，明确不是后台进程总时长。启动、后台延续、write_stdin结束不齐全时不猜测执行时间。

## 请求、用量与实际工具

`settled_requests`去重网关request ID计数；`request_ref`是批次身份与request ID的SHA256。`input_tokens`包含`input_cached_tokens`；`output_tokens`包含reasoning子集。`total_tokens=input+output`，`input_cache_hit_ratio=cache/input`。`requests_with_cache_field/requests_with_reasoning_field/requests_with_cost_record`限制各聚合的完整性；部分已知reasoning总和不是完整推理总数，完全未记录时空。费用只是冻结单价估算，没有接入逐请求账单。

`request_tool_inventory_observed_requests`来自实际request-observation，`actual_tool_names_observed`只保留能读到的工具名称，`tool_inventory_entries_with_unknown_name`保留未知项；工具名不是完整参数schema、版本或权限范围。`prompt_fingerprints_observed`是不同提示指纹数，0表示该批记录没有捕获，不代表请求没有提示。冻结manifest SHA对应本地配置意图，不能替代逐请求开放清单。公开包不发完整提示/工具参数，原始脱敏快照留本地。`reported_native_versions`仅为当前SQLite解析可得版本，其他空值从冻结manifest保留出处，不编造统一值。

## 子身份与回传

`child_count/child_created`基于原生session parent/thread edge或agent.created，而不是模型文字、spawn意图或工具可用。`agents.csv`区分创建、自身独立模型响应、工具记录、实际开始、结果发送、父接收及进入后续模型请求。空值代表未观测/未统一核验，不能改成False。工具0可以与模型工作True并存；子取消和失败不冒充成功终态。公共child ID不是凭据。

## 自检与结果闭环

从真实工具输入里的pytest、python检查脚本、typed-check等识别检查。结果优先显式exit/check字段，缺结果记未知。`recognized_check_tools/recognized_checks_passed/recognized_checks_failed/recognized_check_results_unknown`提供覆盖；未识别不是没有自检。`check_time_sec`只在已识别检查均有span时长时给值。

`self_check_loops.csv`关联失败检查、后续模型/变更工具与复验；`classification`区分相关窗口和证据不完整，`missing_evidence`保留原因，`timing_basis`给时钟来源。`analysis_of_failure_observed=False`是该分析器没有正向证据，不是模型没有思考。`post_failure_window_ms/observation_window_ms`及model/fix/recheck子对象的union/lower_bound不是额外自检的因果成本；`pure_self_reflection_incremental_time_sec`和对应成本保持空，因为缺反事实无法识别。旧`actual_tool_parallelism_status/self_check_loop_time_status`是先前统一重审标志，不覆盖本次新增逐字段覆盖信息。

## 汇总及可复现边界

`summary.csv`仅205有分行；API微平均为通过和/分母和，宏平均为各题准确率均值，缓存率按tokens加权；时间不含无分attempt。`paired_cells.csv`保留104对状态，101对双方有分才进入paired_summary，已核对相同API检查ID集合。不同时间/预算/模型有效模式不能直接作因果排名。

`verify.py`核验公开CSV/JSON之间的一致性与所有文件SHA。`provenance.json`记录本地原件相对身份和SHA，可供持有原件者复核；公开包不含原始会话、题目候选、思维链和凭据，因此单靠公开包不能重新执行verifier或验证全部隐藏trace事实。
