# mixed16-v4 五 Harness 正式实验报告

报告日期：2026-10-30  
实验版本：`mixed16-precise-spec-v4`  
模型：`deepseek-v4-pro`  
并发：5  
任务数：16  
Harness：Nanobot / LangGraph / OpenCode / Codex / DSH  
Trial 总数：80

---

## 一、实验设置

### 1.1 任务

- 数据集：`mixed16-precise-spec-v4`
- 16 个任务，四个 suite 各 4 个：
  - `multistage4`
  - `reasoning4`
  - `context8`
  - `linux2`
- 每个 trial 使用独立 Harbor 环境。
- 评分使用 v4 的 `trusted_validation` 外部 verifier。

### 1.2 Verifier 隔离

v4 的 verifier 和 `_authoring` 已从 agent 镜像移除，改为 **separate verifier environment**：

```text
agent 环境：只有 /app/workspace
verifier 环境：tests/ + trusted_validation/
候选产物通过 artifacts=/app 传入 verifier
```

agent 无法读取 verifier 或 `_authoring`。

### 1.3 指标口径

- **ACC**：reward 1 / 已完成 trial。
- **E2E**：`result.started_at → finished_at`，包含环境启动、agent setup、agent execution、verifier。
- **Agent exec**：`agent_execution.started_at → finished_at`。
- **成本**：`deepseek-v4-pro` off-peak 价格：
  - cache hit：$0.022 / 1M tokens
  - cache miss：$0.66 / 1M tokens
  - output：$1.98 / 1M tokens
- 汇率：**1 USD = 6.7138 CNY**（2026-10-30 人民币对美元中间价，来源：[中国货币网](https://www.chinamoney.com.cn/chinese/bkccpr/)）。
- 所有 80 个 trial 都使用 5 并发，因此 E2E 数据同构。

---

## 二、总体结果

```text
完成：80 / 80
Reward 1：40
ACC：50.00%
E2E 平均：942.2s = 15.70 min
E2E 中位数：782.9s = 13.05 min
Agent exec 平均：911.6s = 15.19 min
总成本：$12.3120 / ¥82.6605（不含 3 个 Codex missing）
平均成本：$0.1539 / ¥1.0333
成本/成功：$0.3078 / ¥2.0665
```

### 2.1 按 Harness

| Harness | 完成 | Reward 1 | ACC | E2E 平均 | Agent 平均 | 成本（USD） | 成本（CNY） | 平均成本（USD） | 平均成本（CNY） | 成本/成功（USD） | 成本/成功（CNY） |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DSH | 16 | 13 | **81.25%** | 14.34 min | 13.82 min | $3.4059 | ¥22.8665 | $0.2129 | ¥1.4292 | $0.2620 | ¥1.7590 |
| Codex | 16 | 10 | **62.50%** | 25.19 min | 24.69 min | $3.6351 | ¥24.4053 | $0.2272 | ¥1.5253 | $0.3635 | ¥2.4405 |
| OpenCode | 16 | 10 | **62.50%** | 17.53 min | 17.02 min | $0.4662 | ¥3.1300 | $0.0291 | ¥0.1956 | $0.0466 | ¥0.3130 |
| Nanobot | 16 | 6 | **37.50%** | 16.06 min | 15.58 min | $3.5647 | ¥23.9327 | $0.2228 | ¥1.4958 | $0.5941 | ¥3.9888 |
| LangGraph | 16 | 1 | **6.25%** | 5.40 min | 4.85 min | $1.2401 | ¥8.3258 | $0.0775 | ¥0.5204 | $1.2401 | ¥8.3258 |
| **合计** | **80** | **40** | **50.00%** | **15.70 min** | **15.19 min** | **$12.3120** | **¥82.6605** | **$0.1539** | **¥1.0333** | **$0.3078** | **¥2.0665** |

---

## 三、结果解读

### 3.1 准确率

- **DSH 最高**：81.25%（13/16）。
- **Codex、OpenCode 并列第二**：62.50%（10/16）。
- **Nanobot**：37.50%（6/16）。
- **LangGraph 最低**：6.25%（1/16）。

LangGraph 的低 ACC 不能解释为“执行更快”：

```text
LangGraph E2E 平均 5.40 min
```

它的 trial 多数在早期结束，主要失败模式仍是未完成交付物。

### 3.2 E2E 时间

- **Codex 最慢**：25.19 min。
- **OpenCode 17.53 min，Nanobot 16.06 min，DSH 14.34 min**。
- **LangGraph 5.40 min**，但这是因为大量 early fail，不是高效完成。

E2E 包含 verifier 和环境启动，因此与 Agent 执行时间略有差异。

### 3.3 成本

- **总成本约 $12.31 / ¥82.66**。
- **OpenCode 成本最低**：$0.47 / ¥3.13，且 ACC 62.5%，性价比最高。
- **DSH / Codex / Nanobot 成本接近**：$3.41–3.64 / ¥22.87–24.41。
- **LangGraph 成本 $1.24 / ¥8.33，但只成功 1 个**，成本/成功最高。

成本差异主要来自：

1. 输入 token 规模；
2. cache hit 比例；
3. 失败 trial 是否仍消耗大量 token；
4. Codex 部分 trial 的 usage 不可观测。

---

## 四、Trace 并行情况

### 4.1 工具级并发

按 trace 中“同时未完成的工具调用”统计：

| Harness | 有工具并发的 trial | 最大并发工具数 | 工具调用总数 | 可观测性 |
|---|---:|---:|---:|---|
| DSH | 14 / 16 | **9** | 755 | trace 可观测 |
| Codex | 3 / 16 | 3 | 777 | item started/completed |
| LangGraph | 4 / 16 | 3 | 759 | event 时间戳 |
| Nanobot | 3 / 16 | 2 | 934 | event 时间戳 |
| OpenCode | 6 / 16 | 4 | 818 | SQLite part.time.start/end（14/16 可观测） |

结论：

- **DSH 存在明显的工具级并发**，最大 9 个工具同时未完成；
- Codex / LangGraph / Nanobot / OpenCode 都有工具级并发；
- OpenCode 已通过 `opencode.db` 的 `part.data.state.time.start/end` 重建，14/16 可观测；剩余 2 个 trial 的 DB 缺失。

### 4.2 并行分支 / 多 Agent

#### LangGraph

启用了：

```text
HARNESS_LANGGRAPH_PARALLEL_PLAN=1
```

16 个任务中：

```text
plan_observed：10 / 16
parallel_workers 路径：10 / 16
parallel_width 分布：
  1：7
  2：1
  3：2
Reward 1：1
success_parallel：0
```

说明：

- planner / `parallel_workers` 确实被构造并执行；
- 最大并行宽度为 3；
- 但唯一成功的 LangGraph trial **没有走并行路径**；
- 因此“并行 planner 已实际运行”，但在这批任务上**没有带来成功**。

#### 其他 Harness

- Nanobot 有 `branch.opened/joined` 标记，但这些 trial 最大并发工具只有 2，不能证明多 Agent 并行。
- DSH 本轮使用 `HARNESS_DSH_CONDITION=delegation_enabled` 和 delegation policy，但 16 个 trial 的 telemetry 全部是：
  ```text
  subagent_count = 0
  planning_level = P0
  ```
  因此 DSH 的 81.25% 不能直接归因于实际 subagent 并行；它仍然主要体现了工具级并发。
- Codex / OpenCode 没有 subagent 或并行分支证据。

整体结论：

```text
有工具级并发；
LangGraph 有真实 planner + parallel_workers 执行；
但没有观察到“并行分支带来成功”的证据。
```

---

## 五、异常与缺失

### 5.1 执行异常

80 个 trial 的 exception 分布：

| Harness | 无异常 | AgentTimeout | NonZeroAgentExitCode |
|---|---:|---:|---:|
| Codex | 13 | 1 | 2 |
| DSH | 16 | 0 | 0 |
| LangGraph | 16 | 0 | 0 |
| Nanobot | 10 | 0 | 6 |
| OpenCode | 16 | 0 | 0 |

其中：

- **3 个 Codex trial 有异常但 reward 1.0**；
- Nanobot 的 6 个 `NonZeroAgentExitCodeError` 均没有成功；
- 没有 API 402 / 429；
- 没有 Docker compose / getwd 失败；
- verifier 没有 protected hash 异常。

### 5.2 Codex cost missing

有 3 个 Codex success trial 的 token usage 缺失：

```text
codex / api_deprecation_campaign_spec_v4
codex / backup_restore_certification_spec_v4
codex / network_policy_convergence_spec_v4
```

原因：

```text
Incomplete response returned, reason: max_output_tokens
turn.failed
```

最后一轮模型响应达到单次输出上限，Codex 没有发出 `turn.completed`，因此没有 `usage`。

处理：

- ACC 仍计入成功；
- token/cost 记为 `missing`；
- 不填 0，也不做假估算；
- 因此 **总成本 $12.3120 / ¥82.6605 是偏低的下界**。

### 5.3 OpenCode 工具并发已从 SQLite 重建

OpenCode 的 `opencode.txt` 只记录完成后的 `tool_use`，但本地 `opencode.db` 的 `part` 表包含：

```text
part.data.state.time.start
part.data.state.time.end
```

据此可以恢复工具并发区间，结果：

```text
可观测：14 / 16
有工具并发：6 / 16
最大并发工具数：4
```

剩余 2 个 trial 的 DB 缺失，无法判断。

### 5.4 LangGraph 成功 trial 不在并行路径

LangGraph 唯一的成功 trial：

```text
streaming_checkpoint_recovery_spec_v4
```

没有走 `parallel_workers` 路径。  
因此不能把 LangGraph 的 ACC 改善归因于并行规划。

---

## 六、结论

1. **DSH 在准确率上最高（81.25%）**。
2. **OpenCode 在成本效率上最好**（62.5% ACC，成本 $0.47 / ¥3.13）。
3. **Codex 准确率接近 OpenCode，但 E2E 最慢（25.19 min）**。
4. **Nanobot 成功率中等偏低，成本不低**。
5. **LangGraph 只有 6.25%**，并行 planner 已实际运行，但没有转化为成功。
6. 这轮结果比之前 v3 明显更可用：80/80 完成，没有 API/基础设施大面积失败。
7. 成本统计中 3 个 Codex trial missing，实际成本会略高于报告值。
8. 工具并发和并行分支必须区分：
   - DSH 有强工具并发；
   - LangGraph 有真实 parallel planner；
   - 但没有证据表明并行分支带来了成功。

---

## 七、数据文件

- `mixed16-v4-acc-e2e-cost.csv`：80 个 trial 的 ACC / E2E / token / 双币成本明细
- `mixed16-v4-acc-e2e-cost-summary.md`：汇总
- `mixed16-v4-trace-audit.json`：工具并发 / LangGraph planner / 异常审计
- `mixed16-v4-tool-concurrency-audit.md`：工具并发专项

GitHub trace 与逐题分析：

- [mixed16-v4 执行数据](https://github.com/xi474/benchmark/tree/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30)
- [DSH 逐题分析](https://github.com/xi474/benchmark/tree/data/mixed16-v4-execution-2026-10-30/experiments/mixed16-v4-2026-10-30/analysis/dsh)
