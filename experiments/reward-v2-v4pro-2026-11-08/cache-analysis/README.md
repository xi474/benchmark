# 逐任务×Harness输入上下文缓存命中率

本报告是2026-11-08已发布运行结果的离线补充，新增供应商请求0。范围为八臂各56题，共448个选定题位；LATTE四个独立补跑另列，不覆盖原基线。

## 指标定义与覆盖率

**输入缓存命中率 = 缓存命中输入token数 / 输入token数。** 每题跨已结算请求先加总再相除；跨题微平均同样按token加权，宏平均只取有完整覆盖的题目比例。输出tokens不进分母，cache-hit是input的子集，不能再与input相加。

来源是DeepSeek API返回usage中的prompt_cache_hit_tokens或Responses input_tokens_details.cached_tokens，经原网关去重归一为cache_tokens。参考[官方上下文缓存说明](https://api-docs.deepseek.com/zh-cn/guides/kv_cache/)、[Responses usage说明](https://api-docs.deepseek.com/guides/responses_api/)。这不是GPU内部每层K/V缓存的访问命中率，也不提供KV显存或驱逐次数。

447/448个基线题位可给出完整请求覆盖的比例。ROMA original/release_compatibility_program有193次实际发送、192次结算、1次未知，完整比例保持null；只给出已结算部分比例。下表带†的是已知部分，不能称完整比例。CSV数值矩阵的该格留空，覆盖矩阵明确标记partial_unknown_request。缺失不记0；真实返回cache-hit=0且输入>0才是0%。

缓存指标独立于任务质量：invalid_submission、预算跳过或Agent异常仍可有真实已结算usage，继续保留分类，不把它们称为任务成功。AOrchestra两题native summary缺测沿用provider-egress来源，未伪造native总量。

## 八臂56题汇总

| Harness | 输入tokens（已知） | 命中tokens（已知） | token加权命中率 | 完整覆盖题数 |
|---|---:|---:|---:|---:|
| nanobot | 103,321,081 | 102,166,784 | 98.88% | 56/56 |
| opencode | 20,137,160 | 19,426,176 | 96.47% | 56/56 |
| codex | 134,834,743 | 132,760,192 | 98.46% | 56/56 |
| dsh | 56,709,576 | 55,453,568 | 97.79% | 56/56 |
| langgraph | 26,539,193 | 23,866,624 | 89.93% | 56/56 |
| latte-planning-adapted | 33,294,534 | 14,471,808 | 43.47% | 56/56 |
| roma | 108,938,229 | 80,039,168 | 73.47%† | 55/56 |
| aorchestra | 30,369,321 | 34,048 | 0.11% | 56/56 |

比例差异描述的是本批请求的上下文前缀复用，不足以单独归因为Harness架构优劣；不保证输出质量或实际推理加速。

## 逐题矩阵

表格显示百分比；CSV数值为0至1的小数。所有原14、mixed16-v4、Medium26任务均覆盖，不仅是有API评分分母的任务。

### original14

[数值矩阵](matrix-original14.csv) · [覆盖状态矩阵](matrix-coverage-original14.csv)

| 任务 | nanobot | opencode | codex | dsh | langgraph | latte-planning-adapted | roma | aorchestra |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| original/adaptive_access_review | 98.44% | 73.41% | 97.23% | 97.17% | 91.63% | 32.17% | 67.18% | 30.44% |
| original/dependency_release_reasoner | 97.51% | 93.80% | 96.93% | 97.83% | 86.22% | 43.03% | 72.19% | 0.13% |
| original/distributed_trace_recovery | 96.18% | 91.90% | 98.53% | 96.51% | 87.27% | 69.76% | 73.90% | 30.44% |
| original/incident_federation_rebuild | 98.19% | 96.64% | 94.09% | 95.94% | 89.01% | 67.62% | 72.88% | 0.09% |
| original/incident_pipeline_repair | 94.94% | 95.57% | 97.49% | 93.24% | 84.69% | 72.93% | 68.83% | 0.13% |
| original/linux_release_analysis | 96.93% | 97.35% | 95.00% | 97.39% | 93.86% | 53.47% | 76.24% | 0.10% |
| original/linux_supply_chain_recovery | 96.03% | 97.95% | 97.49% | 93.97% | 90.19% | 52.30% | 70.18% | 0.12% |
| original/migration_control_plane | 97.99% | 95.82% | 95.33% | 95.27% | 88.23% | 51.26% | 73.06% | 30.15% |
| original/release_compatibility_program | 97.77% | 95.54% | 92.42% | 96.70% | 90.58% | 92.87% | 70.83%† | 0.20% |
| original/schema_evolution_reasoner | 97.84% | 97.05% | 96.29% | 93.19% | 91.34% | 57.84% | 72.52% | 0.10% |
| original/sdk_compatibility_upgrade | 98.40% | 96.09% | 98.32% | 97.50% | 82.28% | 63.91% | 73.65% | 0.12% |
| original/security_boundary_hardening | 94.36% | 95.58% | 98.58% | 91.03% | 85.00% | 65.03% | 76.52% | 0.26% |
| original/supply_chain_assurance | 98.26% | 95.49% | 95.45% | 95.75% | 90.06% | 38.40% | 68.79% | 0.07% |
| original/tenant_platform_upgrade | 97.71% | 97.98% | 98.01% | 91.88% | 87.48% | 69.65% | 70.39% | 0.26% |

### mixed16-v4

[数值矩阵](matrix-mixed16-v4.csv) · [覆盖状态矩阵](matrix-coverage-mixed16-v4.csv)

| 任务 | nanobot | opencode | codex | dsh | langgraph | latte-planning-adapted | roma | aorchestra |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hard/api_deprecation_campaign_spec_v4 | 99.54% | 97.52% | 97.93% | 99.04% | 86.67% | 45.30% | 74.90% | 0.07% |
| hard/artifact_provenance_release_spec_v4 | 98.72% | 86.01% | 97.59% | 97.88% | 90.27% | 45.07% | 76.26% | 0.05% |
| hard/backup_restore_certification_spec_v4 | 99.02% | 98.43% | 99.11% | 97.69% | 90.56% | 49.22% | 66.75% | 0.07% |
| hard/batch_scheduler_transition_spec_v4 | 96.19% | 96.94% | 98.01% | 98.65% | 80.60% | 50.77% | 72.75% | 0.09% |
| hard/certificate_rotation_readiness_spec_v4 | 99.04% | 94.55% | 97.84% | 96.82% | 89.70% | 41.49% | 75.68% | 0.15% |
| hard/edge_fleet_rollout_spec_v4 | 99.43% | 98.37% | 98.05% | 98.35% | 89.99% | 40.34% | 76.33% | 0.09% |
| hard/identity_federation_transition_spec_v4 | 98.90% | 95.78% | 98.22% | 98.32% | 85.10% | 39.13% | 72.11% | 0.15% |
| hard/network_policy_convergence_spec_v4 | 98.71% | 90.77% | 98.99% | 96.59% | 95.21% | 80.83% | 80.09% | 26.04% |
| hard/observability_retention_upgrade_spec_v4 | 99.19% | 97.36% | 97.38% | 97.19% | 86.16% | 34.01% | 71.47% | 0.08% |
| hard/payment_settlement_reconciliation_spec_v4 | 98.80% | 97.68% | 98.72% | 97.67% | 89.93% | 45.05% | 75.39% | 0.11% |
| hard/regional_failover_readiness_spec_v4 | 98.11% | 96.65% | 98.19% | 96.43% | 88.54% | 37.60% | 54.36% | 0.03% |
| hard/search_index_rebuild_spec_v4 | 99.09% | 84.77% | 99.03% | 97.95% | 81.99% | 62.77% | 64.04% | 0.32% |
| hard/storage_tiering_migration_spec_v4 | 98.83% | 85.73% | 97.63% | 96.32% | 93.99% | 81.35% | 72.69% | 0.09% |
| hard/streaming_checkpoint_recovery_spec_v4 | 98.85% | 96.68% | 98.19% | 96.65% | 81.87% | 34.86% | 72.93% | 0.09% |
| hard/tenant_quota_rebalance_spec_v4 | 99.05% | 99.00% | 98.72% | 97.65% | 67.63% | 50.43% | 75.19% | 0.12% |
| hard/warehouse_cutover_assurance_spec_v4 | 98.67% | 86.76% | 97.48% | 98.24% | 93.26% | 36.42% | 62.79% | 0.08% |

### medium26

[数值矩阵](matrix-medium26.csv) · [覆盖状态矩阵](matrix-coverage-medium26.csv)

| 任务 | nanobot | opencode | codex | dsh | langgraph | latte-planning-adapted | roma | aorchestra |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| medium/MP01 | 98.92% | 97.51% | 99.24% | 96.84% | 85.37% | 70.50% | 72.36% | 0.37% |
| medium/MP02 | 99.29% | 97.45% | 99.48% | 97.30% | 93.83% | 50.20% | 73.71% | 0.18% |
| medium/MP03 | 99.01% | 98.11% | 99.21% | 98.41% | 93.74% | 81.21% | 77.14% | 27.12% |
| medium/MP04 | 99.26% | 91.95% | 99.37% | 98.23% | 85.29% | 79.88% | 74.96% | 0.06% |
| medium/MP05 | 99.07% | 93.63% | 99.30% | 98.07% | 92.72% | 79.44% | 73.45% | 0.11% |
| medium/MP06 | 98.59% | 96.07% | 99.04% | 97.44% | 84.26% | 41.70% | 75.26% | 0.10% |
| medium/MP07 | 99.11% | 93.95% | 98.36% | 98.49% | 90.34% | 39.45% | 73.37% | 0.11% |
| medium/MP08 | 98.55% | 87.24% | 99.28% | 97.80% | 91.42% | 45.62% | 76.53% | 0.13% |
| medium/MP09 | 99.02% | 86.41% | 99.35% | 94.93% | 92.96% | 62.19% | 69.21% | 0.15% |
| medium/MP10 | 99.09% | 96.34% | 99.10% | 98.31% | 87.96% | 71.88% | 75.60% | 0.18% |
| medium/MP11 | 99.05% | 95.05% | 98.92% | 97.78% | 92.12% | 79.54% | 76.03% | 0.25% |
| medium/MP12 | 99.10% | 89.98% | 98.92% | 98.55% | 91.24% | 81.14% | 75.14% | 0.08% |
| medium/MP13 | 99.21% | 93.75% | 98.99% | 97.35% | 83.24% | 61.91% | 71.20% | 0.06% |
| medium/MP14 | 99.19% | 97.89% | 98.74% | 97.00% | 92.34% | 46.73% | 75.67% | 27.12% |
| medium/MP15 | 97.40% | 92.91% | 98.62% | 98.81% | 88.00% | 49.10% | 83.10% | 27.26% |
| medium/MP16 | 99.07% | 89.98% | 98.09% | 97.37% | 93.18% | 39.30% | 77.38% | 0.07% |
| medium/MP17 | 99.08% | 97.09% | 99.02% | 97.81% | 92.42% | 81.21% | 70.06% | 0.14% |
| medium/MP18 | 98.33% | 92.83% | 99.37% | 97.32% | 68.45% | 80.91% | 74.48% | 0.17% |
| medium/MP19 | 99.23% | 93.16% | 99.34% | 98.23% | 80.82% | 81.64% | 78.40% | 27.09% |
| medium/MP20 | 98.70% | 84.71% | 99.19% | 98.29% | 73.24% | 38.80% | 73.80% | 0.15% |
| medium/MP21 | 98.71% | 97.91% | 98.38% | 97.42% | 90.75% | 35.99% | 78.08% | 0.17% |
| medium/MP22 | 99.22% | 93.47% | 97.99% | 98.09% | 94.53% | 31.04% | 76.03% | 0.12% |
| medium/MP23 | 98.88% | 89.54% | 97.70% | 97.25% | 89.64% | 37.60% | 75.80% | 0.06% |
| medium/MP24 | 98.67% | 92.05% | 99.18% | 95.90% | 85.96% | 60.40% | 71.59% | 0.06% |
| medium/MP25 | 98.93% | 98.08% | 98.25% | 97.35% | 66.28% | 38.65% | 72.66% | 27.26% |
| medium/MP26 | 97.81% | 91.18% | 98.14% | 97.36% | 93.02% | 38.35% | 73.44% | 0.13% |

## LATTE四个独立补跑

| 任务 | 原终态分类 | 输入tokens | 命中tokens | 命中率 |
|---|---|---:|---:|---:|
| hard/artifact_provenance_release_spec_v4 | scored | 1,796,209 | 646,272 | 35.98% |
| hard/batch_scheduler_transition_spec_v4 | invalid_submission | 1,004,626 | 420,608 | 41.87% |
| hard/identity_federation_transition_spec_v4 | scored | 1,195,052 | 523,520 | 43.81% |
| hard/tenant_quota_rebalance_spec_v4 | scored | 991,793 | 323,200 | 32.59% |

## 文件与复核

- [448行长表](cells-448.csv)：每题的输入、命中/未命中tokens、完整比例、已知部分比例、请求结算状态、原终态分类与来源hash。
- [结构化JSON](results.json)：448题、4补跑、8臂汇总及24组数据集汇总。
- [八臂汇总CSV](harness-summary-8.csv)、[独立补跑CSV](latte-independent-repeats-4.csv)。
- [生成脚本](../scripts/aggregate_input_cache_rates.py)与[独立校验器](../scripts/validate_input_cache_rates.py)，均无需模型或凭据。原七臂和AOrchestra来源JSON字节不变。

生成：python scripts/aggregate_input_cache_rates.py；验证：python scripts/validate_publication.py。缺测状态、纯native/frozen/adapted标签及所有原reward/API/时间/费用口径保持。
