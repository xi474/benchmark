# 默认实验配置（2026-11-24 起生效，11-25 11:15 更新）

本文件定义 Act III 实验线的标准（默认）配置。后续实验除非显式声明变体，一律按此配置执行。

**最终默认栈（2026-11-25 11:15 更新）**：
`ON 臂语义并行 + ②公开检查主动对拍纪律 + FILE EDIT DISCIPLINE（apply_patch/write_file 纪律）+ write_file 条件门（自建文件/占位 stub 放行覆盖，其余强制 apply_patch）+ 反例门控 v2 + shell 写审计 + 自动重放（公开失败最多一次，best-of-2）+ 真实端到端口径`

（变更记录：write_file 硬门 → 条件门——v35 消融证实硬门是 MP25/N22 丢失元凶；v37 证实 ON+条件门下 MP22 翻回 strict。）

## 执行配置

| 项 | 值 |
| --- | --- |
| 语义并行 | **ON 臂**（arm='on'，parallel-v2 active：真实前沿握手 / offer / fork） |
| 运行时镜像 | **`semserve-runtime:default`**（从规范源码 `.../runtime/src/agent_runtime_demo` 构建，`docker commit` 法，Cmd=`sleep infinity`） |
| 镜像注入 | 改写 plan 顶层与**所有 arms** 的 image/image_id；移除全部 `agent_runtime_demo` overlay 挂载（旧挂载会覆盖烘焙代码） |
| 并发 | 4 路（ThreadPoolExecutor max_workers=4） |
| **重放策略** | **公开验证失败的题目自动重放一次（全新 attempt、同配置），取 best-of-2（K 高者，同 K 比 reward）；首次公开通过则不再重放**（2026-11-24 固化，MP19 首跑 6/22 公开失败 → 重放 22/22 strict ✓ 实证有效） |
| 任务集 | 默认 7 题近失带（C031, C055, MP19, MP24, MP26, C074, MS02）；深失带按需指定 |
| 评分镜像 | V2.1 题用 `u59-<tid>:2.1`；V2.0 题用 `u59-<tid>:2.0`（V21_TASKS 全量：C031/C055/C074/MS02/C011/C033/C039/C049/C058/MS11） |
| 对比基线 | `full59_metrics_with_replay.json`（strict/K/A/reward/e2e/cost） |

## 运行时门控（默认开启，已合入规范源码）

1. **② 公开检查主动对拍纪律**（output_guard.py 的 PROMPT，root 系统提示词）：公开检查失败时**不得猜测**——必须①用 public_input.json 跑交付入口、②读 public_expected.json 逐字段比较、③列出每条 `$.path: expected X got Y`、④apply_patch 定点修复后重跑。这是 Codex 翻正 C039/MS11 的真实机制形态（v28 实证：C058 3→6，模型主动对拍 776 次读期望 / 4150 次比较提及）。
2. **反例门控 v2**（runtime.py COUNTEREXAMPLE_GATE_PROMPT，分支交付前）：schema 逐字段规则 + TOKEN LITERALITY（记号逐字一致、禁翻译）+ 全树逐字段比对；原反例原期望复验、期望不可改、3 轮限次。
3. **write_file 条件门**（tools/workspace.py）：覆盖已存在文件时——①模型本会话创建/修改过的文件（authored_paths 登记）放行；②明确占位 stub（≤2 行且含 todo/placeholder/stub/notimplemented 或纯注释）放行；③其余拒绝并引导 apply_patch。新建文件正常。apply_patch 成功即登记 authored。行为已在容器内 4 项验证通过。
4. **shell 工作区写审计**（tools/shell.py）：每次 shell 执行前后快照工作区；已有**代码文件**（.py/.js/.ts/.java/.c/.h/.cpp/.rs/.go/.sh/.rb/.php）被修改/删除 → 自动还原并在结果中报告；新建文件与非代码文件放行并记录。审计上限 64MB，跳过 __pycache__/.git/.semserve。
5. **apply_patch**：已有代码文件的唯一合法修改路径（old_text 精确匹配，失败返回最佳近似提示）。
6. **工具可见性埋点**（runtime.py）：每次模型请求前 emit `tool_schema_visibility` 事件，记录实际发送的工具清单。

**已回滚（不再使用）**：③ 运行时字段级 diff 注入（shell 公开检查失败后由运行时算 diff 塞入工具结果）——被动注入形态与 Codex 真实机制不符，被 ② 替代（v27 验证后回滚，v28 起移除）。

## 度量口径

- strict / K / A / reward：`score()` 用 u59 评分镜像 `test.sh` 产出 score.json。
- **e2e / 成本：真实端到端口径**——重放题 = 首跑 + 重放之和（重放只在首跑结束后才开始）；基线为 full59 同口径。
- 成本单价（从基线表反解固定）：input $0.659843/M、cache-hit $0.022/M、output $1.981869/M。
- 语义证据：semantic_mode_audit.jsonl（enabled/controller）、trace 的 branch 数、offer 事件数。

## 关键历史教训（为什么这么配置）

1. v12 镜像注入只改顶层 plan → runner 用 `plan['arms'][arm]`，实际跑旧镜像（container_receipt 实锤）。
2. overlay 挂载会把烘焙代码覆盖回旧仓库版 → 必须移除 agent_runtime_demo 挂载。
3. `docker create <base> echo ok` + commit 会把 Cmd 写坏（echo ok → 容器秒退）→ 构建必须 create 不带命令（继承 `sleep infinity`）。
4. 仅 write_file 硬门不够：模型绕道 shell 重定向改文件（v15 单题 shell 2005 次、两题全毁）→ 必须加 shell 写审计。
5. 领域语义题 OFF 串行更强（C033 翻正）；边界/工程题 ON 并行隔离更稳——按题目家族分臂。
6. MUST 提示词块在 cli.py V1 而生效的是 V5，且 run_case_live 自建系统提示词 → 约束要落在工具行为与系统提示词（PROMPT），不依赖 cli 常量。
7. 被动注入的诊断（③）不如主动纪律（②）：信息必须出现在模型的推理闭环里（Codex 行为实证）。
8. heldout 型边界题的期望含题面外约定（MP15 字段语义、MP21 大小写），提示词自检有天花板。

## 默认入口

- Driver：`actiii_default_driver.py`（自动 `docker image inspect` 解析镜像 ID；自动重放；真实端到端口径）
- 结果：`default_run/default_results.json` + `default_summary.json`
- 历史对照：v15（OFF 无审计）/ v16（OFF+审计）/ v17-v18（ON+审计）/ v19-v22（反例门控与重放）/ v23-v24（深失带 ON/OFF）/ v25-v26（C039/MS11 翻正）/ v27（③ 验证后回滚）/ v28（② 入默认栈）
