# Nanobot/OpenCode × 三档提示 × 修订六题：V4 Pro普通模式

本轮36个选定题位已全部处理并取得Harbor评分：**12个历史原生结果复用，24个新试次；22个正常终态、14个预算或输出上限异常终态**。新批于**2026-11-11 13:50:28（北京时间）**结束，没有自动付费重试。

**显式委派触发了真实子Agent：Nanobot6/6题、14子；OpenCode5/6题、11子。25个子身份均有各自的模型响应及工具工作。** 原生与软提醒两套均未观测到创建；其中预算截断的零子试次不能作为正常自主不委派的证据。

## 实验配置与可比边界

- 数据集固定为`adapted6-core-v3`：MP04/08/09/10/11/24，Git tree为`e5dcfe62aec12bad2dd9eac3cbec36184a22fe07`。正式任务、初始workspace及verifier未修改；不是后来新增的medium30。
- 模型`deepseek-v4-pro`普通模式，实际请求`thinking.type=disabled`；Nanobot-ai0.3.5、OpenCode1.19.4，同一预装镜像。新批实际峰值5个Harbor trial，父子模型请求共享HTTP≤4。
- 三档分别为原生、可选软提醒、显式要求至少两个有实际工作的不同子Agent。新增两档仅在根入口追加通用提示，不由适配器自动创建子Agent；完整提示和SHA见[conditions.json](conditions.json)。原生12格经相同题目、适配器、工具与限额准入后复用。
- 三档均继承**单响应8192输出tokens、累计2M观测输入＋输出tokens保护阈值**；方案中的32768输出建议没有实施，也没有只给软提醒设置特殊限制。保护统计包含缓存输入和重复上下文，已在途响应可能使最终累计值略超阈值。
- 每组仅6题、每格一个选定attempt；原生控制与新增实验非同期。以下速度、质量与成本差异均是本次描述性观察，不能归因于multiagent本身或外推为总体成功率。

## 子Agent触发与任务质量

| Harness | 条件 | 有分／题位 | 正常／异常 | 子Agent触发率（全6题） | 正常题触发 | 子ID数 | API微平均 | 核心全过题 |
|---|---|---|---|---|---|---|---|---|
| Nanobot | 原生 | 6/6 | 4/2 | 0/6 (0.0%) | 0/4 | 0 | 137/142 (96.5%) | 3/6 |
| Nanobot | 软提醒 | 6/6 | 4/2 | 0/6 (0.0%) | 0/4 | 0 | 129/142 (90.8%) | 1/6 |
| Nanobot | 显式委派 | 6/6 | 3/3 | 6/6 (100.0%) | 3/3 | 14 | 138/142 (97.2%) | 1/6 |
| OpenCode | 原生 | 6/6 | 3/3 | 0/6 (0.0%) | 0/3 | 0 | 59/142 (41.5%) | 0/6 |
| OpenCode | 软提醒 | 6/6 | 3/3 | 0/6 (0.0%) | 0/3 | 0 | 56/142 (39.4%) | 0/6 |
| OpenCode | 显式委派 | 6/6 | 5/1 | 5/6 (83.3%) | 5/5 | 11 | 114/142 (80.3%) | 3/6 |

API通过率指外部verifier中`api/`核心转换用例的通过数／总数，**不是模型供应商HTTP请求成功率**。每组总分母142；宏平均另列于summary.csv。核心检查共196项／组，核心全过与正常终态分别统计。

**评分保留实际运行的original-core-v3政策，单题上限2。没有按仓库后来提出的50%完整交付奖励重评，也没有把未验证的严格验收补算为通过。** 逐格reward、完整核心与API分子分母见[cells.csv](cells.csv)，逐项检查见[verifier-checks.jsonl](verifier-checks.jsonl)。

OpenCode显式唯一未触发题为MP04，在8192输出上限终止、核心0/35，故显式组为5/6；其5个正常题均创建子Agent。Nanobot显式6题均创建，其中3题仍触发累计保护；创建成功不能替代正常完成或质量达标。

## 耗时、tokens与输入缓存

| Harness | 条件 | E2E中位秒（全部） | E2E中位秒（正常） | 输入tokens合计 | 输出tokens合计 | 输入缓存命中率 | 选定试次估算USD |
|---|---|---|---|---|---|---|---|
| Nanobot | 原生 | 371.0 | 358.5 | 9,024,222 | 155,877 | 98.8% | 1.157534 |
| Nanobot | 软提醒 | 371.0 | 332.6 | 9,540,770 | 167,962 | 98.9% | 1.220692 |
| Nanobot | 显式委派 | 493.3 | 494.9 | 10,878,723 | 185,432 | 97.7% | 1.539144 |
| OpenCode | 原生 | 109.0 | 105.1 | 1,344,880 | 51,380 | 94.8% | 0.351143 |
| OpenCode | 软提醒 | 140.8 | 160.9 | 1,641,503 | 56,361 | 95.7% | 0.384796 |
| OpenCode | 显式委派 | 208.9 | 214.5 | 3,794,073 | 93,722 | 95.2% | 0.768566 |

E2E统一重新从每格原始Harbor `started_at` 到 `finished_at` 计算：含环境／安装、Agent执行及评分收尾，不含排队等待。全部列含异常题截至终止的时长，正常列仅包含正常终态。原选择表的新试次外层wrapper另有启动／退出开销，原值也保留在`original_selected_e2e_sec`，不混作统一E2E。Agent执行区间、E2E均值与逐题值见CSV。模型请求时长的累加会包含重叠，不能当E2E或自检耗时。

tokens按网关**唯一已结算请求ID去重**，包含主Agent和所有子Agent；不再额外累加原生子用量，避免重复。输入tokens已包含缓存输入。缓存命中率是供应商返回的cached-input／input，不是模型内部KV-cache容量或利用率。耗时和token比较受输出／累计保护、非同期资源竞争和任务完成程度影响，不能把更早失败当速度优势。

## 子工作与结果回传证据

- Nanobot：`agent.spawned`及parent关系确认14个不同子身份；14子均有`agent.run.started`、独立模型响应、工具记录及结果发送证据。本次链路只明确观测到2子父接收；其余父接收、14子后续模型输入尚未完整关联，记未知。
- OpenCode：原生SQLite `session.parent_id`递归确认11子，均有各自模型响应和工具记录；11子Task结果均已由父会话接收，且回传内容哈希与后续模型请求工具结果相符。独立“发送事件”字段未覆盖，记未知。
- 原Nanobot汇总的`started=false`只检查了`agent.started`这一hook；v0.3.5实际发出的是`agent.run.started`。本报告追加14个派生旁注，保留原冻结输出。OpenCode模型工作仅计有usage或完成证据的assistant记录，排除空占位，见[audit-addenda.json](audit-addenda.json)。
- **子Agent创建、实际模型／工具工作、结果回传闭环与工具级真实并行分别认定。** 本报告没有对全部工具span重新配对，也没有统一量化自检关联窗口；工具级并行峰值和自检净耗时记未知，不以子数量或HTTP峰值代替。

## 14个异常终态

| Harness | 条件 | 任务 | 原终态标签 | 核心评分 | 子数 |
|---|---|---|---|---|---|
| Nanobot | 原生 | MP04 | scored_with_uniform_usage_cap | 32/35 | 0 |
| Nanobot | 原生 | MP09 | scored_with_uniform_usage_cap | 38/38 | 0 |
| Nanobot | 软提醒 | MP04 | scored_with_uniform_usage_cap | 31/35 | 0 |
| Nanobot | 软提醒 | MP08 | scored_with_uniform_usage_cap | 19/27 | 0 |
| Nanobot | 显式委派 | MP04 | scored_with_uniform_usage_cap | 34/35 | 2 |
| Nanobot | 显式委派 | MP08 | scored_with_uniform_usage_cap | 26/27 | 2 |
| Nanobot | 显式委派 | MP10 | scored_with_uniform_usage_cap | 29/30 | 3 |
| OpenCode | 原生 | MP04 | scored_with_agent_output_cap | 0/35 | 0 |
| OpenCode | 原生 | MP08 | scored_with_agent_output_cap | 0/27 | 0 |
| OpenCode | 原生 | MP24 | scored_with_agent_output_cap | 0/36 | 0 |
| OpenCode | 软提醒 | MP04 | scored_with_agent_output_cap | 0/35 | 0 |
| OpenCode | 软提醒 | MP09 | scored_with_agent_output_cap | 0/38 | 0 |
| OpenCode | 软提醒 | MP10 | scored_with_agent_output_cap | 0/30 | 0 |
| OpenCode | 显式委派 | MP04 | scored_with_agent_output_cap | 0/35 | 0 |

7个累计保护、7个单响应输出上限终态均保留原attempt及原评分。带分异常不叫正常完成；截断零子不作为自由选择不委派的充分证据。没有为取得正例重跑或删除失败。

## 请求结算与费用

本次**新增24试次：1177/1177请求结算、unknown0、active0，估算USD3.913198432**。复用12格的395个历史已结算请求没有再次产生费用；36格选定结果合计1572个请求、历史加本轮估算USD5.421875272。两种范围分开报告，不能将历史消费算作这次新增消费。

估算沿用封存的每百万tokens峰价：未缓存输入USD1.32、缓存输入USD0.044、输出USD3.96，公式`((input-cache)*1.32 + cache*0.044 + output*3.96)/1e6`。**这是历史冻结价目估算，不是供应商账单，也不是本次重新查询的实时价格。** 全部逐请求输入／输出／缓存、时长和估算见[request-usage.csv](request-usage.csv)，`reused`区分历史与新增。本36格unknown0不代表其他历史实验的未知用量已经结清。

## 文件与复核

- [task-matrices.md](task-matrices.md)：六题×六条件的API、子数量、E2E、tokens和核心检查矩阵。
- [cells.csv](cells.csv)、[cells.json](cells.json)：36格完整白名单指标；[summary.csv](summary.csv)、[summary.json](summary.json)：六组微／宏平均、正常子集及计量定义。
- [agents.csv](agents.csv)：25个实际子身份及独立模型／工具工作、发送／接收／后续输入证据；[anomalies.csv](anomalies.csv)：14个异常。CSV空单元格与JSON null表示未知或未观测。
- [provenance.json](provenance.json)：原始评分、结果、原生身份、脱敏工具／提示和账本SHA；771个冻结源文件重新校验通过。[validation.json](validation.json)、[SHA256SUMS](SHA256SUMS)用于核验导出内容。

本次只做离线分析和用户授权的结果发布，没有新模型请求、任务／verifier修改或付费重跑。只上传白名单指标、通用条件提示和校验哈希；本地原始trace、环境凭据、个人路径、私有MLP材料及第三方Harness源码不随报告分发。
