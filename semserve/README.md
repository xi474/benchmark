# SemServe Upstream59 重放实验档案（2026-11-20 ~ 11-21）

SemServe（自感知并行 Agent Runtime）在 Upstream59 v2.0.0 / v2.1.0 上的完整在线重放：执行 trace、评分结果、指标与报告。全部运行使用同一冻结配置（DeepSeek V4 Pro 官方 API + docker-linux + `h3a-value-v2-branch-profiles-run-tests-v1` runtime profile + Qwen3-32B value_v2 预测器 @ 10.27.127.9），评分使用发布方 delivery-bonus-50-v1 官方验证器。

## 实验目录

| 目录 | 内容 | 规模 |
|---|---|---|
| `20261120-upstream59-mp10-current-v1/` | MP10 十题重放（v2.0.0，59 账的第一块） | 10 题 |
| `20261120-upstream59-rest49-current-v1/` | 其余 49 题重放（v2.0.0：15 MP + 20 C + 10 MS + 4 N） | 49 题 |
| `20261121-v21-pilot-v1/` | v2.1.0 模块化 C/MS 试点（C008/C069/C017/MS02） | 4 题 |
| `20261121-v21-cms30-v1/` | v2.1.0 模块化 C/MS 全量重放（30 题）——**统一 59 题总账主目录** | 30 题 |
| `20261121-pubfail9-rerun-v1/` | 9 题公开失败重放（Retry-on-Public-Fail 验证） | 9 题 |
| `20261121-replay-mechanism-design.md` | 重放机制设计（clean-P 触发、上限 1 次）与增益分析 | — |
| `_archived_j1_j2c/` | J1/J2-c 提示词许可负结果档案（设计文档 + J1 取证数据） | — |

## 每个实验目录的结构

- `experiment_plan.json` / `tasks.json` / `run_status.json` / `preflight.json` / `cache_namespaces.json` / `fixture_manifests/` —— 封印与运行状态（sha 锁定任务字节与挂载）
- `run.py` / `u59_score.py` / `predictor_access.py` / `actor_adapter.py` —— 实验编排与评分脚本
- `online/on/cases/<entry>/dynamic_v7/` —— 每题执行档案：
  - `trace.jsonl`：**完整执行 trace**（runtime 事件流：frontier 握手、验证反馈、Offer、fork/join、DAG 等）
  - `qwen-predictions.jsonl`：value_v2 预测器决策记录
  - `deepseek_cache_isolation.jsonl`：API 调用与 KV cache 审计
  - `semantic_mode_audit.jsonl` / `host_receipt.json` / `result.json`：模式审计与宿主回执
  - `workspace/`：agent 产出的最终工作区（官方评分的输入）
  - `u59/`：官方验证器逐题评分（score.json / raw-checks.json / container_output.txt）
- `u59_score_report.json` / `metrics*.json` / `parallel*.json` / `report.md` —— 汇总指标与报告

## 统一 59 题总账（入口）

`20261121-v21-cms30-v1/report.md`（重放机制应用版）+ `full59_metrics_with_replay.json`（机器可读逐题全指标）。
最终账面：严格 28/59（47.5%）、公开 56/59（94.9%）、API acc 669/803（83.3%）、reward 85.362/138、KV 命中 90.0%、总成本 $22.06。

## 体积说明（为控制仓库体积的排除项）

以下大体积消息转储**未纳入**本提交（本地留档，可按需补交）：每题的 `turns.jsonl`（完整对话日志，~600MB）、`speculative_turns.jsonl`（握手投机轮消息快照，~160MB）、`handshake_inputs.jsonl`（H3A 线缆快照，~250MB）。执行事件流（trace.jsonl）、预测器决策、缓存审计、评分与工作区**全部包含**。两次启动误跑的归档（`_misfire_*`）与物化任务输入（`actor_inputs/`，与仓库 `tasks/` 重复）亦未纳入。

## 密钥与安全

提交前已扫描全部待提交文件（17,639 个小文件 + 328 个大日志）：无私钥、API key、Bearer token 或口令。日志中出现的 `10.27.127.9` 为 RFC1918 内网地址（预测器 SSH 入口），无凭据泄露风险。
