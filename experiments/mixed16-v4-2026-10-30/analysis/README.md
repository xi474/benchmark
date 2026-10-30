# mixed16-v4 逐题执行分析

本目录包含 Codex / OpenCode / Nanobot 三个 Harness 在 16 个 v4 任务上的逐题分析。
完整原始 trace 位于 `../traces/`，机器可读汇总为 `summary.csv`。

## codex

- 任务数：16
- Reward 1：10
- ACC：62.50%
- E2E 平均：1511.2s（25.19 min）
- Agent 平均：1481.6s
- 成本：$3.6351 / ¥24.4053
- missing cost：3
- 有工具并发 trial：3 / 16；最大并发工具：3

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 1.0 | 3630.808 |  |  | AgentTimeoutError |
| artifact_provenance_release_spec_v4 | 0.0 | 993.512 | 0.299884 | 2.0134 | {"status": "failed", "reason": "held-out API mismatch: views/release_risk case 1"} |
| backup_restore_certification_spec_v4 | 1.0 | 2935.473 |  |  | NonZeroAgentExitCodeError |
| batch_scheduler_transition_spec_v4 | 0.0 | 2345.86 | 0.525722 | 3.5296 | {"status": "failed", "reason": "held-out API mismatch: engines/worker_assignment case 3"} |
| certificate_rotation_readiness_spec_v4 | 1.0 | 1270.394 | 0.280939 | 1.8862 | {"entry": "linux2/certificate_rotation_readiness_spec_v4", "status": "passed", "output_count": 5, "api_cases": 26, "protected_file_count": 1 |
| edge_fleet_rollout_spec_v4 | 0.0 | 1649.617 | 0.291225 | 1.9552 | {"status": "failed", "reason": "held-out API mismatch: engines/rollout_order case 3"} |
| identity_federation_transition_spec_v4 | 1.0 | 2137.669 | 0.397821 | 2.6709 | {"entry": "context8/identity_federation_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 27, "protected_file_count": |
| network_policy_convergence_spec_v4 | 1.0 | 1597.387 |  |  | NonZeroAgentExitCodeError |
| observability_retention_upgrade_spec_v4 | 0.0 | 886.817 | 0.162755 | 1.0927 | {"status": "failed", "reason": "incorrect output: outputs/archive_logs.json"} |
| payment_settlement_reconciliation_spec_v4 | 1.0 | 625.37 | 0.126341 | 0.8482 | {"entry": "context8/payment_settlement_reconciliation_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_coun |
| regional_failover_readiness_spec_v4 | 1.0 | 1019.204 | 0.271374 | 1.822 | {"entry": "multistage4/regional_failover_readiness_spec_v4", "status": "passed", "output_count": 9, "api_cases": 37, "protected_file_count": |
| search_index_rebuild_spec_v4 | 1.0 | 903.435 | 0.200687 | 1.3474 | {"entry": "context8/search_index_rebuild_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 18} |
| storage_tiering_migration_spec_v4 | 0.0 | 1301.121 | 0.391972 | 2.6316 | {"status": "failed", "reason": "held-out API mismatch: views/migration_waves case 1"} |
| streaming_checkpoint_recovery_spec_v4 | 1.0 | 987.137 | 0.267741 | 1.7976 | {"entry": "context8/streaming_checkpoint_recovery_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count":  |
| tenant_quota_rebalance_spec_v4 | 1.0 | 1130.926 | 0.286959 | 1.9266 | {"entry": "reasoning4/tenant_quota_rebalance_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| warehouse_cutover_assurance_spec_v4 | 0.0 | 764.158 | 0.131661 | 0.8839 | {"status": "failed", "reason": "held-out API mismatch: views/repair_waves case 1"} |

## opencode

- 任务数：16
- Reward 1：10
- ACC：62.50%
- E2E 平均：1051.8s（17.53 min）
- Agent 平均：1021.2s
- 成本：$0.4662 / ¥3.1301
- missing cost：0
- 有工具并发 trial：6 / 16；最大并发工具：4

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 0.0 | 801.454 | 0.024482 | 0.1644 | {"status": "failed", "reason": "held-out API mismatch: engines/notice_windows case 5"} |
| artifact_provenance_release_spec_v4 | 0.0 | 563.264 | 0.018428 | 0.1237 | {"status": "failed", "reason": "incorrect output: outputs/audit_assignment.json"} |
| backup_restore_certification_spec_v4 | 1.0 | 1122.441 | 0.029097 | 0.1953 | {"entry": "linux2/backup_restore_certification_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 13} |
| batch_scheduler_transition_spec_v4 | 1.0 | 1622.209 | 0.042962 | 0.2884 | {"entry": "reasoning4/batch_scheduler_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 1 |
| certificate_rotation_readiness_spec_v4 | 0.0 | 1239.139 | 0.032027 | 0.215 | {"status": "failed", "reason": "held-out API mismatch: products/trust_graph case 5"} |
| edge_fleet_rollout_spec_v4 | 1.0 | 1560.963 | 0.029564 | 0.1985 | {"entry": "reasoning4/edge_fleet_rollout_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| identity_federation_transition_spec_v4 | 0.0 | 1748.71 | 0.030767 | 0.2066 | {"status": "failed", "reason": "held-out API mismatch: authorization case 6"} |
| network_policy_convergence_spec_v4 | 1.0 | 619.533 | 0.024255 | 0.1628 | {"entry": "linux2/network_policy_convergence_spec_v4", "status": "passed", "output_count": 5, "api_cases": 31, "protected_file_count": 13} |
| observability_retention_upgrade_spec_v4 | 0.0 | 1464.365 | 0.02336 | 0.1568 | {"status": "failed", "reason": "incorrect output: outputs/archive_logs.json"} |
| payment_settlement_reconciliation_spec_v4 | 1.0 | 601.169 | 0.032803 | 0.2202 | {"entry": "context8/payment_settlement_reconciliation_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_coun |
| regional_failover_readiness_spec_v4 | 1.0 | 518.877 | 0.022308 | 0.1498 | {"entry": "multistage4/regional_failover_readiness_spec_v4", "status": "passed", "output_count": 9, "api_cases": 37, "protected_file_count": |
| search_index_rebuild_spec_v4 | 1.0 | 1439.251 | 0.043125 | 0.2895 | {"entry": "context8/search_index_rebuild_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 18} |
| storage_tiering_migration_spec_v4 | 1.0 | 396.064 | 0.016505 | 0.1108 | {"entry": "multistage4/storage_tiering_migration_spec_v4", "status": "passed", "output_count": 8, "api_cases": 37, "protected_file_count": 1 |
| streaming_checkpoint_recovery_spec_v4 | 1.0 | 923.537 | 0.025053 | 0.1682 | {"entry": "context8/streaming_checkpoint_recovery_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count":  |
| tenant_quota_rebalance_spec_v4 | 0.0 | 1509.619 | 0.045229 | 0.3037 | {"status": "failed", "reason": "held-out API mismatch: engines/operator_assignment case 3"} |
| warehouse_cutover_assurance_spec_v4 | 1.0 | 698.571 | 0.02627 | 0.1764 | {"entry": "multistage4/warehouse_cutover_assurance_spec_v4", "status": "passed", "output_count": 8, "api_cases": 37, "protected_file_count": |

## nanobot

- 任务数：16
- Reward 1：6
- ACC：37.50%
- E2E 平均：963.7s（16.06 min）
- Agent 平均：935.0s
- 成本：$3.5647 / ¥23.9329
- missing cost：0
- 有工具并发 trial：3 / 16；最大并发工具：2

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 0.0 | 582.413 | 0.077153 | 0.518 | NonZeroAgentExitCodeError |
| artifact_provenance_release_spec_v4 | 0.0 | 551.265 | 0.089364 | 0.6 | NonZeroAgentExitCodeError |
| backup_restore_certification_spec_v4 | 0.0 | 527.3 | 0.09027 | 0.6061 | NonZeroAgentExitCodeError |
| batch_scheduler_transition_spec_v4 | 0.0 | 743.736 | 0.074873 | 0.5027 | NonZeroAgentExitCodeError |
| certificate_rotation_readiness_spec_v4 | 1.0 | 1281.053 | 0.292993 | 1.9671 | {"entry": "linux2/certificate_rotation_readiness_spec_v4", "status": "passed", "output_count": 5, "api_cases": 26, "protected_file_count": 1 |
| edge_fleet_rollout_spec_v4 | 0.0 | 2494.384 | 0.686604 | 4.6097 | {"status": "failed", "reason": "held-out API mismatch: engines/rollout_order case 3"} |
| identity_federation_transition_spec_v4 | 1.0 | 1374.424 | 0.322464 | 2.165 | {"entry": "context8/identity_federation_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 27, "protected_file_count": |
| network_policy_convergence_spec_v4 | 1.0 | 1329.208 | 0.296162 | 1.9884 | {"entry": "linux2/network_policy_convergence_spec_v4", "status": "passed", "output_count": 5, "api_cases": 31, "protected_file_count": 13} |
| observability_retention_upgrade_spec_v4 | 0.0 | 1204.328 | 0.239323 | 1.6068 | {"status": "failed", "reason": "incorrect output: outputs/archive_logs.json"} |
| payment_settlement_reconciliation_spec_v4 | 1.0 | 786.226 | 0.169203 | 1.136 | {"entry": "context8/payment_settlement_reconciliation_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_coun |
| regional_failover_readiness_spec_v4 | 1.0 | 973.245 | 0.295695 | 1.9852 | {"entry": "multistage4/regional_failover_readiness_spec_v4", "status": "passed", "output_count": 9, "api_cases": 37, "protected_file_count": |
| search_index_rebuild_spec_v4 | 0.0 | 967.998 | 0.276072 | 1.8535 | {"status": "failed", "reason": "held-out API mismatch: cutover_plan case 6"} |
| storage_tiering_migration_spec_v4 | 1.0 | 1015.618 | 0.306654 | 2.0588 | {"entry": "multistage4/storage_tiering_migration_spec_v4", "status": "passed", "output_count": 8, "api_cases": 37, "protected_file_count": 1 |
| streaming_checkpoint_recovery_spec_v4 | 0.0 | 459.429 | 0.077447 | 0.52 | NonZeroAgentExitCodeError |
| tenant_quota_rebalance_spec_v4 | 0.0 | 483.031 | 0.075129 | 0.5044 | NonZeroAgentExitCodeError |
| warehouse_cutover_assurance_spec_v4 | 0.0 | 645.691 | 0.1953 | 1.3112 | {"status": "failed", "reason": "held-out API mismatch: views/repair_waves case 1"} |

## 说明

- Codex 有 3 个 success trial 因 `max_output_tokens` / `turn.completed` 缺失，成本为 missing。
- OpenCode 有 2 个 trial 的本地 SQLite DB 缺失，工具并发无法观测。
- 工具并发不等于多 Agent 并行；详细 trace 并发审计见交付报告。
