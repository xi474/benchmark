# Codex三个缺分题位：R7 Chat普通模式独立补跑

发布于2026-11-13T20:00:33.952243+08:00。MP19先通过有效评分、实际出口/工具/提示/资源/原生父子及用量门禁，随后MP15、MP17自动并行。**3/3均获得有效Harbor评分，旧attempt及历史未知用量保留。**

## 数据与版本边界

- 数据为原Medium26剔除规格问题六题后保留的`medium20-original`中的MP19/15/17；不是仓库新`parallel20-calibrated-medium-v1`。任务/verifier原文件哈希保留，沿用score-v2 2.0.0，单题上限2，未按新50%交付政策重评。
- 固定Codex CLI0.164.0、DeepSeek V4 Pro、32768单响应上限、相同显式委派提示与权限、相同镜像。新的`responses-chat-normal-v1.0.4`将客户端Responses转为上游Chat `thinking.type=disabled`；实际出口逐请求留证。
- [experiment.json](experiment.json)记录配置意图、版本/限额、镜像与任务文件hash；[request_tools.csv](request_tools.csv)记录实际请求开放的工具名、namespace、类型和schema hash，[request_prompt_hashes.csv](request_prompt_hashes.csv)记录实际提示指纹。原prompt及完整schema脱敏快照留本地，不用“配置打算开放”代替实际请求证据。
- 3题请求和响应均通过本批模式契约门禁；未观测到返回reasoning矛盾。供应商数值reasoning字段缺失仍保留空，不能冒称测得0推理token。
- 这是独立修复适配版，**不把旧原生/显式49个有分结果改标为已验证普通模式，也不将不同适配版本混成严格同配置排名**。旧[205个有分结果快照](../explicit-medium20-core6-four-harness-v4pro-20261112/README.md)保持不变。
- 原来3个无分逻辑题位现在均有独立新评分；按选择身份可补齐104个显式题位，但包含旧版与R7两个适配层，需保留分层。历史原生对照并非强制单Agent消融。

## 原始评分与耗时

| 任务 | reward/2 | 核心通过 | API通过 | API准确率 | 子Agent | E2E秒 | Agent秒 | verifier秒 | 终态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MP19 | 1.777778 | 24/27 | 16/19 | 84.21% | 2 | 608.5 | 584.3 | 10.6 | normal |
| MP15 | 1.538462 | 30/39 | 22/29 | 75.86% | 2 | 854.9 | 829.9 | 11.6 | normal |
| MP17 | 1.866667 | 28/30 | 20/22 | 90.91% | 3 | 1070.6 | 1048.2 | 10.5 | normal |

API是原verifier `api/`检查通过率，不是模型HTTP成功率。3题合计API **58/70（82.86%）**，逐项ID与相同历史原生题一致；不同模式与适配版本不作因果收益结论。

E2E用Harbor原始finished_at减started_at，不含入队等待；Agent/verifier分别是原生阶段时长。异常标签保持原值，不能把有效有分一概写成正常完成。子数量是创建证据，工作、回传和进入后续请求分别见[agents.csv](agents.csv)，不代表工具进程真实并行。

7个子身份中，7个均有自身独立模型工作证据；6个完成，6个有父接收及后续请求证据，1个被取消。取消者是MP19的一名子Agent，其已有自身模型/工具工作，但未观测最终回传，不称7个全部完成协作，也不据此单独归因评分缺失。

## tokens、缓存及费用

| 任务 | 输入tokens | 输出tokens | 缓存输入tokens | 输入缓存率 | 已结算估算USD | 拒绝未开放调用 | 归一化历史请求 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MP19 | 4,623,813 | 59,327 | 4,537,984 | 98.14% | 0.547900496 | 8 | 0 |
| MP15 | 4,394,751 | 66,682 | 4,294,656 | 97.72% | 0.585150984 | 3 | 0 |
| MP17 | 7,588,841 | 106,537 | 7,412,480 | 97.68% | 0.980832160 | 3 | 26 |

本R7已结算估算合计 **USD2.113883640**，不是账单。价格快照仍为每百万输入miss USD1.32、缓存输入0.044、输出3.96。输入已含缓存，输出已含reasoning子集，不重复相加。缓存率为供应商报告的缓存输入tokens/输入tokens，不是底层KV-cache容量或逐层命中率。逐请求去重记录见[request_usage.csv](request_usage.csv)。

[batch_ledger.json](batch_ledger.json)仅对应R7。历史R1/R2物理批未知10、R3修复未知3继续保留；新的unknown0不结清旧13条，也不代表旧费用为0。R3/R4/R5/R6失败原件均留本地，不用本次成功覆盖。已知历史物理新批成本、复用题位成本和R7成本范围不同，不能混加称实际账单。

## 修复内容与真实观测

1. 未开放工具调用不执行、不在工具清单注册；以不可执行保留名交给CLI原生unsupported-tool错误反馈，保留调用ID，让正常会话继续。没有网关模型重试，没有将未知工具映射成更高权限功能。拒绝调用和工具成功分列。
2. Responses可出现“调用A/B→返回B→调用C→返回C/A”的交错历史。R7仅对传输表示合并仍开放的assistant工具组，保留所有调用参数、结果内容、调用顺序和结果相对顺序；不造结果、不移动政策/用户指令屏障。原native执行时序不改，不能把规范化后的顺序当真实调度。
3. 离线覆盖9项旧协议、5组工具拒绝、6组历史检查、真实R6参数/结果片段HTTP回放以及固定CLI network-none机制回归。机制测试不计入benchmark成功率。额外子会话direct-resume探针因CLI未加载parent而被拒绝的限制保留，不计通过。

真实拒绝数与历史归一化请求数见表和[transport_events.csv](transport_events.csv)。计数为0表示本次未触发该修复分支，不表示没有能力。创建和处理错误反馈不自动等于完整协作闭环。

## 资源和监控限制

| 任务 | 模型HTTP elapsed总和秒 | 容器采样数 | 采样内存峰值MiB | 采样CPU秒 | 工具span完整数/总数 |
| --- | --- | --- | --- | --- | --- |
| MP19 | 758.0 | 583 | 209.3 | 13.26 | 0/139 |
| MP15 | 848.4 | 827 | 170.8 | 13.25 | 0/119 |
| MP17 | 1321.1 | 1045 | 184.4 | 17.24 | 0/127 |

- 容器cgroup采样、模型请求elapsed、API、E2E、用量已从原件核对；内存是采样峰值，CPU是可比累计值差，不是逐子Agent资源或供应商GPU耗时。模型HTTP elapsed求和可因并发超过E2E，不能与E2E相加。
- Codex工具span缺可比起止时保持未知，不使用日志接收时间、UI事件时间或write_stdin墙钟片段拼完整进程时长。真实OS工具并行和逐Agent cgroup没有统一完整采集。
- 自检命令/失败关联窗口与纯自检增量开销不同；未捕获的分析、修复或复验阶段保持未知，不能用模型文字推断耗时。[self_check_loops.csv](self_check_loops.csv)仅为关联证据。
- 原生工具记录可能包含本次被拒绝的调用、失败或待定状态；不能直接当成功执行量。准确子工作与回传的正向证据/未知分别在agents.csv。

## 离线复核

运行`python verify.py`，无需网络、API或依赖。核对SHA、3题唯一性、逐项API与历史分母、原始Harbor时间、去重tokens/cache/价格快照、子身份及账本。公开包只含脱敏表格和来源hash，不含原prompt、CoT、候选代码、完整会话或凭据。原件留本地，公开包一致性校验不替代重执行verifier。

- [cells.csv](cells.csv)：逐任务完整指标、状态和覆盖率。
- [verifier_checks.csv](verifier_checks.csv)：逐项检查ID/通过位/类别及来源SHA。
- [agents.csv](agents.csv)：独立子身份、模型/工具工作及结果回传证据。
- [validation.json](validation.json)、[provenance.json](provenance.json)、[SHA256SUMS](SHA256SUMS)：核验结果与来源。
