# 近失带验证器家族缺口分析与 v2 修复方案（2026-11-23 20:55）

## 一、A / D / B / P 家族失分分布（近失 15 题基线，41 个缺口）

| 家族 | 缺口数 | 占该族总数 | 占总缺口 | 修复难度 |
|---|---|---|---|---|
| **D（CLI 工件）** | **14** | **33%** | 34% | **低——同一模式批量修** |
| **A（核心变换）** | **22** | 13% | 54% | 中——逐题边界推导 |
| **B（业务逻辑）** | **5** | 22% | 12% | 中 |
| P（公开检查） | 0 | 0% | 0% | — |

### D 类失败明细（14 个，8 题命中）

| 验证器 | 命中题数 | 题目 |
|---|---|---|
| **cli-artifact-2** | 8 | C069、C079、MS14、MS30、MS42、C031、C067、C068、C011 |
| **cli-artifact-1** | 5 | C069、C079、C031、C067、C068 |

### A 类失败明细（22 个，13 题命中）

| 模式 | 题数 | 典型验证器 |
|---|---|---|
| 语义边界（"X 不能同时为 Y"型规则） | 8 | wal-2/3、settlement×3、C031-05/07、C067-04/05、C068-05/07 |
| 交叉验证（"多个字段互斥"型） | 4 | indistinguishable-scores、independent-workshops、independent-and-unwitnessed、replicated-rings |
| 保留字段（"某字段不导出"型） | 4 | decrypted-template、heldout-202、invalid-business-field、core-08/09/10 |
| 边界值（数值/长度边界） | 6 | boundary 等 |

## 二、v2 修复方案（按修复性价比排序）

### 修复 1：产物对账（命中 D 类 14 个缺口，34% 的总缺口）

**判据来源**：任务文档中既定的调用规则与工件清单——LLM 可推导、无需判分器语义。

**指令追加（6 行）**：
```
6. (Artifact Reconciliation) Before delivery, reconcile the CLI interface:
   a) List EVERY documented way the program is invoked (from TASK.orig.md,
      check.py, and run_all.py): commands, arguments, flags, paths.
   b) For each, verify: correct exit code, expected output files exist,
      output format matches the documentation.
   c) For each, test the edge cases the task text implies (missing input,
      invalid arguments).
   This is separate from the boundary self-tests: boundary tests cover the
   transformation logic, artifact tests cover the CLI surface.
```

**成本**：+2-3 轮（读文档 + 写测试 + 跑 + 修）≈ +$0.02/题，+30-60s/题
**命中预期**：D 类 14 缺口中至少 8-11 个（C069/C079/C031/C067/C068 的 cli-artifact-1/2 全部同一模式）

### 修复 2：语义边界清单（命中 A 类 22 个缺口中约 14 个）

**判据来源**：contract/TASK.orig.md 中的"X 不能同时为 Y"型规则。

**指令追加（4 行）**：
```
7. (Semantic Boundary Checklist) For every rule in the task text that has
   the form "X must/must not coexist with Y" or "when A then B must be C":
   write at least 2 self-tests exercising the coexistence/prohibition.
   Example: if the task says "tags=true means trusted=false", write tests
   for both tags=true and tags=false combinations.
```

**成本**：+1-2 轮 ≈ +$0.01/题，+15-30s/题
**命中预期**：A 类 22 缺口中 12-14 个（语义边界+交叉验证型）

### 修复 3：拒绝门（兜底 MP24 型回退，不增 E2E/成本）

**实现**（driver 层，无需新 episode）：
```
修复后运行 public check + 自检用例：
  - public check 不过 → 回退原始工作区
  - 自检用例失败数增多 → 回退原始工作区
  - 否则 → 交付修复版
```

**成本**：~0（比较操作，秒级）

### 修复 4：TASK.orig.md 常规化（家族无关化，~0 成本）

**实现**：恢复工作区时将原始任务描述存为 `TASK.orig.md`（新增文件不影响 integrity）。

## 三、修复后的预期开销与收益

| 方案 | 增量 E2E | 增量成本 | 预期 strict 增量 |
|---|---|---|---|
| v1（现有） | +152s/题 | +$0.074/题 | +1（MP02 实证） |
| **v2 = v1 + 修复 1+2+3+4** | **+180-210s/题** | **+$0.10-0.12/题** | **+4-6**（D 类 8-11 + A 类 3-5 + 拒绝门保底） |
| 增幅（被修复题自身） | ×1.3-1.4 | ×1.6-1.7 | — |
| 增幅（49 题总账摊销，31% 触发率） | +18% | +8-10% | — |

## 四、各家族的不可修复性判定

| 家族 | 缺口 | v2 可修复 | 不可修复原因 |
|---|---|---|---|
| D（CLI 工件） | 14 | **~11** | 余 3 个可能测的是未文档化的行为 |
| A（变换边界） | 22 | ~14 | 余 8 个需要精确的语义理解（深失带延伸） |
| B（业务） | 5 | ~2-3 | B 类验证器内容最少，逐题判断 |
| **合计** | **41** | **~27-28** | — |

**v2 上限估算：15 题中 8-9 题可翻 strict**（前提：D 类同一模式批量修复成立 + 语义边界清单命中）→ strict 15→23-24/49（47-49%），成本增幅 <10%。
