# Upstream59 v2.1.0 模块化 C/MS 试点报告

**实验目录**：`CurrentV7/results/20261121-v21-pilot-v1/`
**日期**：2026-11-21 15:10（在线运行 8m55s，并发 2）
**上游**：benchmark 快进到 `669bc93`（v2.1.0，含 `d15d560`），30 个 C/MS 任务全部模块化重构
**配置**：纯冻结基线（deepseek-official-pro + h3a-value-v2 profile + Qwen3-32B 预测器）——**零提示词改动**，只有任务字节变了

## 1. v2.1.0 结构变化（J2-a 的实现）

每题从"单 solution.py"重构为 **2 组件 + 1 汇聚层**：

```
components/<A>/{work.py 占位, check.py, input.json, expected.json, run.py, README.md}
components/<B>/{...}
integration.py（combine 占位）
component_runtime.py（run/check/join 哈希）
work_units.json（声明单元与其 run/check 命令）
solution.py（delegates to component_runtime）
```

与 MP 家族的 domains/views 结构同构：**每组件一个占位实现面 + 一个独立验证器**。

## 2. 试点结果（4 题全 completed）

| 题 | 握手宽度(v2.0→v2.1) | 预测器 | Offer | fork 子分支 | 真实重叠 | strict |
|---|---|---|---|---|---|---|
| C008 | 1 → **2** | 2× parallel_ready | 接受 | 2（33.0s/36.5s） | **33.0s** | ✓ 2.0/2 |
| C069 | 1 → **2** | 2× parallel_ready | 接受 | 2（48.5s/21.4s） | **21.4s** | **✓ 3.0/3（K 13/13）** |
| C017 | 1 → **2** | 2× parallel_ready | 接受 | 2（24.1s/16.4s） | **16.4s** | ✗ 0.75/3 |
| MS02 | 1 → **3** | 2× parallel_ready | 接受 | **3**（37/16.8/51.8s 同时启动） | **16.8s+** | ✓ 3.0/3 |

**全链路真实执行**：宽度打开 → 预测器全接受 → Offer 接受（choose_execution_mode_v2 explicit decision）→ `fork_only_child_envelope` 分支 fork → 子分支并行执行（时间区间重叠）→ `branch_completed_from_verified_artifact` → `parallel_v2_plan_completed` → `root_integration_checkpoint_activated` → post-join watch 收束。

## 3. 三个决定性观察

1. **预测器决策随结构正确翻转**：同一预测器（value_v2）在 v2.0 单文件 C008 上判 `serial`（j2c 冒烟 2 次 serial），在 v2.1 组件化 C008 上判 `parallel_ready`（2 次）——8/8 全接受。**"预测器区分度不足"的表象其实是任务结构问题**：结构对了，预测器立刻给出正确答案。
2. **C069 业务正确率显著提升**：K 11/13 → **13/13 strict**（v2.0 基线 1.269 → 3.0 满分）。注意 v2.1 的 registry 把 C069/C017 的 max_reward 从 2 调到 3（"pre-run implementation structure review" 结构评审加权），reward 绝对值跨版本不可直接比，但 strict 与 K/N 可比：C069 从差 2 项到全过。
3. **C017 持平（0.75）**：失败项是 A/C017-02/04/06/08 + B/solution + D/cli-artifact-2——组件实现质量问题（contact_profiles 语义不完整），不是编排问题（其 2 分支照样 fork/join 走通）。

## 4. E2E 与成本

E2E：C008 151s、C069 219.5s、C017 284.8s、MS02 145.6s（合计 801s）。**与 v2.0 不可直接比**（任务本身变了：组件化后多了独立检查与 join 的工作量）。MS02 在 3 分支并行下 E2E 145.6s 还略快于 v2.0 串行的 154.7s。

## 5. 结论

v2.1.0 的模块化重构**完全打通了 C/MS 家族的语义并行**：握手宽度、预测器、Offer、fork、真实重叠、join 收束、评分全链路走通，且正确率不降反升（1 升 3 持平 0 降）。与 J1/J2-c 双负结果合并成完整因果链：

> **提示词许可（J1/J2-c）无效，任务结构（v2.1.0 = J2-a）完全有效**——实现面数量与每单元独立验证器决定并行是否发生；预测器、宽度门、Offer 机制在此结构上全部正确工作。

后续建议：30 题 C/MS 全量 v2.1 重放（与 v2.0 rest49 基线对照，reward/K 分列、注明 max_reward 加权变化）、MS02 的 integration 分支语义（作为并行分支是否合理）复盘、C017 组件质量分析。

## 6. 产物索引

- 封印/计划：`experiment_plan.json` / `tasks.json` / `run_status.json` / `fixture_manifests/` / `preflight.json`
- 在线 trace：`online/on/cases/context8/<tid>/dynamic_v7/`（trace.jsonl、speculative_turns.jsonl、qwen-predictions.jsonl、host_receipt.json）
- 逐题评分：`online/on/cases/context8/<tid>/dynamic_v7/u59/score.json`
- 镜像：`u59-{c008,c069,c017,ms02}:2.1`
- 执行日志：`online_run_console.log` / `prepare.log` / `preflight.log` / `ppreflight.log`
