# 单文件交付任务的中间产物并行方案（runtime + 控制面提示词修改设计）

**背景实证**（2026-11-21 全 59 题重放）：C/MS 30 题全部串行的根因是"单写表面"——30/30 题只有一个占位文件（29×solution.py + 1×engine.py），握手 LLM 提议宽度 200×1 + 14×0，`safe_width` 恒 1，宽度门在预测器之前短路。但**单文件交付 ≠ 不可并行**：规范可切分的题可以 producer 写中间产物 → join → merge 消费者合并进交付文件 → 回收中间产物。

## 一、目标形态（三段式）

```
                     ┌─ producer A → .semserve/scratch/<planA>/part_a.json   (focused_check_a)
deliverable.py  ←    ├─ producer B → .semserve/scratch/<planB>/part_b.json   (focused_check_b)
   (merge consumer)  └─ producer C → .semserve/scratch/<planC>/part_c.py     (focused_check_c)
        ↑ needs=[A,B,C]，join 后激活，串行执行，写 solution.py，
          完成后 runtime 确定性回收 .semserve/scratch/
```

## 二、控制面（提示词）修改

### 2.1 位置

- `runtime/src/agent_runtime_demo/tools/workspace.py`：`report_frontier_state` 的 tool schema 与描述（`workload_hint`/`required` 定义处，约 602 行附近）+ 报告指引文本（"If candidate tasks still disagree on an interface ... **edit the same file** ... choose serial" 段）。
- 同文件 G1/branch-profile 扩展点之后的 schema update 区域。

### 2.2 规则文本修改（diff 草案）

**删除**：
```
- If candidate tasks still disagree on an interface, need a missing tool result, edit the same file, or are too small to repay child startup cost, choose serial or decline with that concrete reason.
```
**替换为**：
```
- If candidate tasks still disagree on an interface, need a missing tool result, or are
  too small to repay child startup cost, choose serial or decline with that concrete reason.
- A single-file deliverable does not by itself force serial execution. When the
  specification splits into independently verifiable sub-results, propose producer
  units with artifact_kind="intermediate": each writes disjoint files under
  .semserve/scratch/<work_unit_id>/ and carries its own focused_check that validates
  the sub-result against the contract fragment it owns, without reading any file
  another live producer writes. The final assembly into the deliverable is a later
  serial consumer (artifact_kind="final", needs listing those producers); report it
  only after the producers, never as currently-ready.
- Only propose intermediate producers when each sub-result can be checked standalone
  (a self-contained contract fragment). If sub-results share mutable state or one
  fragment cannot be verified without another's output, stay serial.
```

### 2.3 schema 扩展（ready_upsert 单元新字段）

```json
"artifact_kind": {"type": "string", "enum": ["final", "intermediate"]},
"scratch_paths": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 256},
  "description": "Intermediate-only: disjoint paths under .semserve/scratch/<work_unit_id>/; reclaimed by Runtime after the consumer completes."}
```
- `consumes` 不需要新字段：已有 `needs` 承担（merge 单元的 needs = producer ids）。

## 三、Runtime（数据面）修改

### 3.1 验证层 `dynamic_frontier.py`（583 行，写集/读证/契约校验所在地）

1. **scratch 命名空间强制**：`artifact_kind="intermediate"` 的单元，`write_set` 每个路径必须命中 `.semserve/scratch/<canonical_work_unit_id>/` 前缀；越界即拒（错误码 `scratch_namespace_violation`）。
2. **disjoint 校验扩展**：现有 pairwise 冲突检查（`_paths_overlap`）不变——scratch 路径天然 disjoint；额外禁止两个 intermediate 单元写同一 scratch 子树。
3. **中间产物 completion contract**：`required_artifact_paths` 限 scratch 内；`focused_check` 必须不引用任何 live producer 的写路径（复用 `_g1_validation_state` 的 `validation_inferred_needs` 推导：producer 写集 × 该单元 check 读集无交集）。
4. **merge consumer 语义**：`needs` 非空且指向 intermediate producers 的单元标记 `integration_pending`（机制已有）；其 `read_set` 必须是 producers 的 `scratch_paths` 超集——否则 `merge_reads_incomplete` 拒绝。

### 3.2 宽度门与预测器

- `safe_width` 统计包含 intermediate producers（单文件任务从此可开宽度门）。
- `qwen_frontier_predictor.py` 的 value_v2 输入增加两个特征：`deliverable_surface`（single-file / multi-file）与 `decomposition`（final-only / intermediate+merge）。**预测器必须能看见"这波并行含合并开销"**——child 启动 + merge 成本 vs producer 节省，正是 worth-parallel 该判断的量。
- 上线顺序：先 shadow 模式（预测器只记录不决策，executor 照 Offer 走），收集 C/MS 上的决策分布，再决定是否解冻（与 R1 训练管线衔接：这会改变 C/MS 任务的动作分布，需补 SFT 样本）。

### 3.3 Join 与回收

1. join 处把 producers 的 verified scratch 产物绑定为父上下文的 read evidence（复用 `verified_artifact` 机制，`branch_result_bound_to_verified_artifact` 已有路径）。
2. merge consumer 完成且其 focused_check 通过后，runtime **确定性删除**已声明的 `scratch_paths`，记 trace 事件 `scratch_artifact_reclaimed`（含文件清单 sha）。
3. `output_guard.py` 的根完成协议加一条 cleanliness 断言：final answer 前检查 `.semserve/scratch/` 为空（已有 check.py 执行钩子，顺带执行）。
4. KV 侧无需新机制：fork 子分支私有 KV、join 只回收子生成 KV 的现有语义直接适用；merge 单元在 join 后由父上下文执行。

## 四、护栏（来自本次实验的实证风险）

| 风险 | 证据 | 护栏 |
|---|---|---|
| 规范不可切分 | C017 两模块 `inferred_needs` 互相依赖、C069 状态机咬合 | 提示词保留"无法独立验证就 serial"；`validation_inferred_needs` 非空的单元不得进 ready |
| 题目太小，拆分负收益 | C/MS 中位 E2E 75–130s、题均 $0.08–0.2 | 不在提示词里硬编码阈值——交给 value_v2 预测器把关（这正是它的职责） |
| 中间产物残留污染交付 | 官方 integrity 只查 protected 5 文件，但 cleanliness 影响可信度 | 确定性回收 + output_guard 断言 + reclaim 回执 |
| merge 单元把错误合并进交付 | producer 各自 check 过 ≠ 合并对 | merge 后仍跑整题 public_check（现有 serial_p02 自检通道） |

## 五、实验路径（按冻结基线规范）

1. **离线宽度验证（便宜）**：30 题 C/MS 的 `handshake_inputs.jsonl` 已在案——用新提示词对既有输入重放投机轮（只花握手调用费，不跑全任务），量"LLM 提议宽度分布"从 {1:200, 0:14} 变成什么。
2. **单题冒烟**：C069（规范最重）与 C008（最简单）在线跑，观察 producer→join→merge→reclaim 全链 trace。
3. **30 题全量**：当前冻结配置 + 提示词 overlay（走 experiment 的 mounts overlay 机制，不碰冻结 runtime 主体），对照今天的串行基线：reward / E2E / 成本 / 缓存命中分列报告。
4. **预测器 shadow**：收集 value_v2 对 intermediate 前沿的决策分布 → 决定 SFT 补样或阈值调整。

## 六、修改文件索引

| 层 | 文件 | 改什么 |
|---|---|---|
| 控制面提示词 | `runtime/src/agent_runtime_demo/tools/workspace.py` | serial 规则改写 + schema 扩 `artifact_kind`/`scratch_paths` |
| 验证 | `runtime/src/agent_runtime_demo/dynamic_frontier.py` | scratch 命名空间/disjoint/merge 读集校验 + 新错误码 |
| 预测器 | `runtime/src/agent_runtime_demo/qwen_frontier_predictor.py` | value_v2 输入特征 + shadow 开关 |
| 输出守卫 | `runtime/src/agent_runtime_demo/output_guard.py` | scratch cleanliness 断言 |
| Join/回收 | join 绑定 + 新增 `scratch_artifact_reclaimed` 事件 | 确定性回收与回执 |

## 七、J1-v1 实验结果（2026-11-21 11:53，提示词-only，负结果）

**实验**：J1 只改控制面（握手提示词 + schema），对 30 题 C/MS 的 245 条已归档握手输入离线重放（同模型、同输入，仅提示词不同）。运行至 140/245 时停止（结论已定）：**LLM 提议宽度全部为 0 或 1，零次 ≥2**——与基线分布 {1:200, 0:14} 无行为差异。取证样本（j1_forensic.json，5 题完整响应）：

- C066/MS02 的上报**确实启用了新字段** `artifact_kind="final"`（schema 采纳成功）；
- C008 仍是单单元（write_set 略扩为 solution.py+outputs/result.json）；
- C069/C017 直接 blocked："TASK.md... only inventory-observed, not read"——要求先补读证据。

**失败根因（四层）**：

1. **J1 的护栏条款被忠实执行了**：规则写明"Only propose intermediate producers when each sub-result can be checked standalone"——C/MS 工作区没有任何 per-part 检查素材，模型正确地按规则 stay serial。J1 不是没被读到，而是**按自己的规则得出了与基线相同的结论**。
2. **握手轮是"读者"不是"作者"**：report-only turn 的契约为 "Report only facts learned from tool results"（只报告已观察事实）。发明 scratch 拆分结构是"创作"，与该契约冲突——step-2 的对话证据只有 inventory（未读文件），模型宁可 blocked 也不编造。
3. **证据主导、许可次要**：移除 "edit the same file → serial" 的禁令不改变模型的归纳——它上报的依据是已观察的工作区结构（单占位文件、单一契约、单一整题检查器）。
4. **schema 字段采纳 ≠ 行为改变**：`artifact_kind="final"` 出现说明补丁可见且被消费，但 `intermediate` 从未被使用，因为没有任何已观察证据支持"可独立验证的子结果"存在。

**结论与 J2 方向**：并行机会必须在**主执行轮被创造**（探索期制造可验子结构），握手轮才能报告它。仅改握手提示词无法打开 C/MS 宽度。

- **J2-a（任务打包侧）**：component 家族工作区提供"可选拆分模块"骨架（推广 C017 的 identity_*.py/ledger_*.py 空壳模式，各配 mini-check），把拆分邀请做进任务结构。
- **J2-b（runtime 侧）**：允许 intermediate 单元在报告里自带内联 `check_code`，由 runtime 沙箱验证其自包含可跑——把"可独立验证"素材从工作区搬进报告。
- **J2-c（主执行提示词侧）**：在**主执行**系统提示（非握手轮）加"可为可独立验证的子结果创建 .semserve/scratch/ 中间模块"，让 agent 探索期就建立多表面证据，握手轮才有料可报。

**成本记录**：145 次 DeepSeek 握手重放（~$1–2），j1_replay.py / j1_forensic.py / j1_forensic.json 留档。

## 八、J2-c 冒烟结果（2026-11-21 12:25，主执行提示词许可，负结果）

**实验**：`20261121-j2c-smoke-v1`——在主执行系统提示词（run_case_live.py overlay 的 `cli.NEUTRAL_SYSTEM_PROMPT` 组装处）注入 `[RUNTIME_SCRATCH_DECOMPOSITION]` 段：授权 agent 为可独立验证的子结果在 `.semserve/scratch/` 脚手架子模块（module + module_check），装配后合并进交付文件。其余全部与 rest49 基线一致（runtime、握手规则、schema 未动）。4 题冒烟：C008/C069/C017/MS02（基线均 width-1 串行）。

**结果（4/4 completed，E2E 合计 294.5s）**：

| 题 | 基线 | J2-c | 提议宽度 | scratch 模块 | Offer/子分支 | 预测器 |
|---|---|---|---|---|---|---|
| C008 | strict 2.0 | strict 2.0（K 12/12, A 8/8） | 全 1 | 0 创建 | 0/0 | **2 次调用均 serial**（基线 0 次） |
| C069 | 1.269 | 1.269（同） | 全 1 | 0 | 0/0 | 0 |
| C017 | 0.750 | 0.750（同） | 全 1 | 0 | 0/0 | 0 |
| MS02 | strict 3.0 | **1.269（A 7/9，E2E 155→77s）** | 全 1 | 0 | 0/0 | 0 |

**结论**：

1. **宽度仍未打开**：agent 没有为任何一题创建 scratch 分解模块（`.semserve/` 下只有 runtime 自带的 visible_checks 文件）；4 题全部单单元直做 solution.py、零 Offer 零子分支。主执行端许可与握手端许可（J1）同样无效——**许可不改变行为，结构与经济学才改变行为**：这些任务"单文件小题 + 无 per-part 检查器"的最短可靠路径就是直做，模型理性地选择了它。
2. **唯一正向变化**：C008 的 value 预测器首次被咨询（2 次调用，均正确判 serial）——J2-c 下 frontier 生命周期更完整（inspect→implement→validate 单元跨代累积，到达了预测器；基线 C008 在宽度门就短路）。
3. **MS02 单轮退化**（3.0→1.27，A 9/9→7/9，E2E 减半）：单次观测、无法区分单轮方差与提示词扰动，按规范仅记录不下结论；C008/C069/C017 三题分数与基线逐位相同，整体无系统性回归。
4. **修正方向收敛**：J1+J2-c 双负结果把可行路径压缩到 J2-a（任务打包提供 per-part 桩与检查器——MP 的 23/25 与 C017-baseline 的 width-2 皆源于此）或 J2-b（报告内联 check_code 降低发明子检查的成本）。若两者都不做，则这 30 题的正确答案就是当前行为：串行。

**产物**：`20261121-j2c-smoke-v1/`（overlays/run_case_live.py 补丁、run.py、online/、逐题 u59 回执）。
