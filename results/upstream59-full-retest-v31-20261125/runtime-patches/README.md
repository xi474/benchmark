# runtime-patches：最终默认栈相对基线的全部代码改动

基线 = `semserve-serial-unittest-mixed16:20261101` 镜像内烘焙的 agent_runtime_demo
（2026-11-01 版本）。当前 = 2026-11-25 最终默认栈（镜像 semserve-runtime:default）。
`full-diff.patch` 是完整差异（git 风格，a/=基线，b/=当前）；`changed/` 是改动后文件全量。

## 改动清单与动机

### 1. runtime.py
- `COUNTEREXAMPLE_GATE_PROMPT`（反例门控 v2）：分支交付前强制反例复验——schema 逐字段规则、
  记号字面一致性（禁翻译/大小写改）、全树逐字段比对、原反例原期望复验、期望不可改、3 轮限次。
  动机：u59 边界型题（MP/MS 族）分支交付漏检是失分主因；全量 59 题中 9 题翻正均有门控拒绝事件实证。
- 分支上下文注入（~L3980）：把门控提示注入每个分支的渲染上下文（仅 ON 臂语义并行有分支）。
- `tool_schema_visibility` 追踪事件（~L742）：每次模型请求前记录实际发送的工具清单，
  用于验证 apply_patch 等工具是否真实可见。

### 2. tools/workspace.py
- write_file 条件门（替代原硬门）：覆盖已存在文件时——①本会话模型创建/修改过的文件
  （WorkspaceAccess.authored_paths 登记）放行；②明确占位 stub（<=2 行且含 todo/placeholder/
  stub/notimplemented 或纯注释）放行；③其余拒绝并引导 apply_patch。apply_patch 成功即登记 authored。
  动机：硬门是 MP25（0/25→25/25）、N22（8/19→19/19）丢失的元凶（无门消融实证），
  条件门保留硬门的保护同时恢复 MP/N 族整文件覆盖工作流。
- `_looks_like_placeholder` 启发式。

### 3. tools/shell.py
- 工作区写审计：每次 shell 执行前后快照；已有代码文件（.py/.js/.ts/.java/.c/.h/.cpp/.rs/.go/
  .sh/.rb/.php）被修改/删除自动还原并在结果中报告；新建文件与非代码文件放行记录。
  上限 64MB，跳过 __pycache__/.git/.semserve。
  动机：v15 模型绕道 shell 重定向改文件（单题 2005 次）导致两题全毁。

### 4. output_guard.py
- `PUBLIC CHECK FAILURE DISCIPLINE`（②收敛式 v3）：公开检查失败时一轮收敛——①用 public_input 跑交付入口
  ②逐字段对拍 public_expected ③写出全部 mismatch 清单 ④诊断共同根因、单次 apply_patch 修根因
  ⑤mismatch 不降即停手重读。动机：复刻 Codex 的主动对拍收敛行为（v40 C039：apply_patch 1476→65，
  打转下降 95%+，行为收敛实证）。
- `FILE EDIT DISCIPLINE`：apply_patch 只做小范围定点修改、不整模块重写、改后必测。

## 已回滚、不含在本包内的改动（实验否定）
- ③ 运行时字段级 diff 注入（shell 公开检查失败时运行时算 diff 塞回工具结果）：
  v27 验证被动注入不如主动对拍，回滚。
- apply_patch 批量信封格式（Codex 式 Begin Patch/@@）：v39 验证 DeepSeek 模型
  不适应信封格式（C055 13→0），回滚为单次 old_text/new_text。
- actor 超时 900s 补丁：仅存在于实验 driver（actiii_v32+），不属于运行时镜像源码。

## 配置层（不在本包，见 analysis/default_config.md）
ON 臂语义并行 + 门控 v2 + ②收敛纪律 + 条件门 + shell 审计 + 自动重放（公开失败最多一次，
best-of-2）+ 真实端到端口径（重放题 e2e/成本 = 首跑+重放）。

## 其他差异文件（canonical 自 2026-11-01 基线的既有演进，非本实验线改动）

以下文件与基线的差异来自规范源码在 11-01 至 11-25 期间的其他工作线演进，
本实验线未修改但随当前镜像一并生效；完整差异见 full-diff.patch：
branch_test_delivery.py, classifier_state_memory.py, cli.py, dynamic_frontier.py,
handshake_speculation.py, parallel_control_v2.py, parallel_runtime_v2.py,
progress_recovery.py, qwen_frontier_predictor.py, validation_progress.py,
tools/registry.py, g1_branch_checks.py（新增）, g1_discovery.py（新增）,
progress_recovery_e1.py（新增）。
