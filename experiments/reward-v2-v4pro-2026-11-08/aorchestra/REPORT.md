# 发布说明

本文件为原终态报告的脱敏发布副本；本机路径转换为证据定位符。原始数值和实验标签保持，来源SHA见上级publication-audit.json。以下正文保留原归档语境，其中“同目录”指原始本地归档；本发布文件以本说明中的链接为准。完整指标请读取[results-56.json](results-56.json)，逐题CSV见[cells-56.csv](cells-56.csv)。

# AOrchestra 续行12题终态与56题完整覆盖

用户对manifest `67573979e264778693bbd2b7544fc56c51cb31162fb2a99a1d2a4794d6c32720`明确授权后，公开Mixed16剩余12题各执行一次，批次complete。先证书轮换pilot，再最多4 trial并发/共享全局5；模型deepseek-v4-pro，thinking显式disabled，160请求/4096输出、每题USD5。北京时间2026-11-07T23:45:06.063272+08:00至2026-11-08T00:17:16.667760+08:00。原18题及历史Medium26未补跑，没有扩题或付费消融。

## 本次12题

12/12独立评分且完整性通过，reward **2.846744/36**，归一化7.9076%；满分0、部分分2、0分10。API检查21/334，微平均6.2874%、宏平均8.5840%。

编排状态{"failed": 9, "completed": 3}，原因{"non-stop-model-terminal": 8, "model-submit": 3, "JSONDecodeError": 1}。各题最后响应的finish_reason、输出tokens、角色、请求ID及脱敏异常堆栈见逐题JSON；length与4096上限对应，但未做更高cap消融，不推出充分因果。JSON解析异常与length分别统计，历史5个TypeError的原始原因仍未知。

子Agent实际触发11/12题，共20个运行时配置实例；4题共12次reviewer响应/摘要回传，按delegation ID逐条配对；显式主Agent submit 3次。摘要可能为部分结果，不代表子任务通过。Python Agent类固定，不将配置实例计为新类合成。

题内多Agent并行0题、子Agent峰值1、handoff 0；工具537个、失败终态51、未闭合0、工具并发峰1。跨任务HTTP dispatch-to-settlement峰4只表示批次并发。

供应商828次请求全部结算，客户端尝试828、严格证实的本地未出站拒绝0、unknown/inflight 0/0。input 6528472、output 215486、cache-hit 6400（输入子集）；角色usage逐项见JSON。本次12题native summary均可观测；父批2题的原生总量仍保持null/unavailable，不能用供应商egress总量改写。吞吐量仅为非流式客户端往返口径，非推理引擎decode速度。

续行峰价估算USD9.462741200，加原18题USD16.871920208，原USD50授权合计 **USD26.334661408**；invoice=null，不冒充账单实付。预算没有重置，未使用旧Medium26授权余额。

## 完整覆盖与比较边界

原14题reward 4.357143/14；Medium26 6.997009/52；Mixed16 5.595882/48。选定56唯一题位共 **16.950034/114**，归一化14.8685%；满分3、部分14、0分39。这是按各数据集max_reward加权的reward归一化，不能替代逐题准确率。API与原14的focused命名空间分列；API微平均13.5014%、宏平均13.9812%，focused 17/54。

56题实际子Agent触发47题、配置实例108、摘要回传80、题内并行0题。编排{"failed": 37, "completed": 19}。全部选定结果费用估算USD44.448758552含历史独立授权Medium26，不能当作本轮USD50扣费。历史两个排除attempt、原18题raw stopped/旁注、旧JSON/CSV与诊断版本均保留。完整30题导出的complete表示两阶段题位合并完成；原父批raw status仍stopped，本次续行独立批次为complete。全部56题评分不等于56题正常提交，更不代表论文原条件或公平等限额排名。

Provided DAG未注入；Harness Control DAG单列；Observed Model Plan DAG仍unavailable，不从工具顺序或委派指令补造；Execution DAG、Agent Topology与工具级并发分别来自实际事件。当前12 workflow验证0 errors/12 warnings，警告均为无显式Plan快照；累计56为0/56。task-container资源本次4329样本、累计20102，采样仅覆盖Agent执行窗口，不覆盖安装与verifier。per-agent cgroup延后；远程GPU/显存/KV cache/queue/batch/engine tokens/s/能耗均null。

shared-workspace、同模型reviewer、reserve-review-and-submit-v1、4096/160、原生串行委派均为适配条件；后12题仅宿主usage验收采用显式注册provider-egress-local-reservation-v1。未改变原生prompt、解析、调度、重试、模型runtime或网关策略。各Harness有效上限并不完全一致，因此按带条件标签的比较臂纳入矩阵，不能解释为上游性能上限。

## 验证、文件与下一步

Windows与固定镜像network-none各41项离线回归通过（本轮新增6项）；12题逐项宿主审计、模型请求SHA/usage对账及workflow验收通过。终态导出和selected56合并独立离线重放；JSON/CSV逐字一致。不读取额外凭据，不发新模型调用。原formal仓库保持feature/workflow-observability-v2@1e7e782及其原13个tracked修改；未访问私有私有数据，原归档时未push/merge；本结果发布另获明确授权。

本报告：`results-aorchestra-continuation12-2026-11-08.md`；本次12、完整30及完整56分别附同目录JSON/CSV。旧2026-11-07部分覆盖文件不改。原始WSL证据根`aorchestra-batches/mixed16-remaining12-local-reservation-r2-20261107`，离线入口`harbor-agents/scripts/audit_aorchestra_continuation12.py`及`export_aorchestra_selected56.py`无需key。

下一步仅离线核对跨Harness参数、终态策略及失败结构；任何扩题、提高cap或付费消融另行预注册并取得授权。
