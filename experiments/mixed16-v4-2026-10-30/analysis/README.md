# mixed16-v4 逐题执行分析

本目录包含 7 个实验条件在 16 个 v4 任务上的逐题分析。
完整原始 trace 位于 `../traces/`，机器可读汇总为 `summary.csv`。

## LATTE 两种版本

- `latte-native`：`HARNESS_LATTE_NATIVE=1`，LATTE 原生动态发现任务。
- `latte-injected`：adapter 读取 `/opt/latte-task` 的预编译组件任务，属于注入提示/固定任务版本。

## Codex (`codex`)

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

## OpenCode (`opencode`)

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

## Nanobot (`nanobot`)

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

## DSH (`dsh`)

- 任务数：16
- Reward 1：13
- ACC：81.25%
- E2E 平均：860.4s（14.34 min）
- Agent 平均：829.3s
- 成本：$3.4059 / ¥22.8667
- missing cost：0
- 有工具并发 trial：14 / 16；最大并发工具：9

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 1.0 | 952.411 | 0.246317 | 1.6537 | {"entry": "reasoning4/api_deprecation_campaign_spec_v4", "status": "passed", "output_count": 5, "api_cases": 28, "protected_file_count": 12} |
| artifact_provenance_release_spec_v4 | 0.0 | 813.15 | 0.231608 | 1.555 | {"status": "failed", "reason": "held-out API mismatch: views/release_risk case 1"} |
| backup_restore_certification_spec_v4 | 1.0 | 734.115 | 0.182574 | 1.2258 | {"entry": "linux2/backup_restore_certification_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 13} |
| batch_scheduler_transition_spec_v4 | 1.0 | 1352.192 | 0.310388 | 2.0839 | {"entry": "reasoning4/batch_scheduler_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 1 |
| certificate_rotation_readiness_spec_v4 | 1.0 | 863.961 | 0.20063 | 1.347 | {"entry": "linux2/certificate_rotation_readiness_spec_v4", "status": "passed", "output_count": 5, "api_cases": 26, "protected_file_count": 1 |
| edge_fleet_rollout_spec_v4 | 1.0 | 1209.899 | 0.295111 | 1.9813 | {"entry": "reasoning4/edge_fleet_rollout_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| identity_federation_transition_spec_v4 | 1.0 | 758.59 | 0.171774 | 1.1533 | {"entry": "context8/identity_federation_transition_spec_v4", "status": "passed", "output_count": 5, "api_cases": 27, "protected_file_count": |
| network_policy_convergence_spec_v4 | 1.0 | 779.506 | 0.207883 | 1.3957 | {"entry": "linux2/network_policy_convergence_spec_v4", "status": "passed", "output_count": 5, "api_cases": 31, "protected_file_count": 13} |
| observability_retention_upgrade_spec_v4 | 0.0 | 997.105 | 0.25749 | 1.7287 | {"status": "failed", "reason": "incorrect output: outputs/archive_logs.json"} |
| payment_settlement_reconciliation_spec_v4 | 1.0 | 525.532 | 0.129303 | 0.8681 | {"entry": "context8/payment_settlement_reconciliation_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_coun |
| regional_failover_readiness_spec_v4 | 1.0 | 598.359 | 0.176291 | 1.1836 | {"entry": "multistage4/regional_failover_readiness_spec_v4", "status": "passed", "output_count": 9, "api_cases": 37, "protected_file_count": |
| search_index_rebuild_spec_v4 | 1.0 | 772.384 | 0.200634 | 1.347 | {"entry": "context8/search_index_rebuild_spec_v4", "status": "passed", "output_count": 5, "api_cases": 32, "protected_file_count": 18} |
| storage_tiering_migration_spec_v4 | 0.0 | 602.904 | 0.160526 | 1.0777 | {"status": "failed", "reason": "held-out API mismatch: views/migration_waves case 1"} |
| streaming_checkpoint_recovery_spec_v4 | 1.0 | 675.863 | 0.163236 | 1.0959 | {"entry": "context8/streaming_checkpoint_recovery_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count":  |
| tenant_quota_rebalance_spec_v4 | 1.0 | 1544.686 | 0.314826 | 2.1137 | {"entry": "reasoning4/tenant_quota_rebalance_spec_v4", "status": "passed", "output_count": 5, "api_cases": 21, "protected_file_count": 12} |
| warehouse_cutover_assurance_spec_v4 | 1.0 | 585.244 | 0.157331 | 1.0563 | {"entry": "multistage4/warehouse_cutover_assurance_spec_v4", "status": "passed", "output_count": 8, "api_cases": 37, "protected_file_count": |

- DSH condition：`delegation_enabled`；但 telemetry `subagent_count` 全部为 0。
- 因此这轮 DSH 的 ACC 提升不能直接归因于实际 subagent 并行。

## LangGraph (`langgraph`)

- 任务数：16
- Reward 1：1
- ACC：6.25%
- E2E 平均：323.9s（5.40 min）
- Agent 平均：290.7s
- 成本：$1.2401 / ¥8.3254
- missing cost：0
- 有工具并发 trial：4 / 16；最大并发工具：3

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 0.0 | 219.785 | 0.02967 | 0.1992 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| artifact_provenance_release_spec_v4 | 0.0 | 214.031 | 0.034585 | 0.2322 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| backup_restore_certification_spec_v4 | 0.0 | 638.984 | 0.199204 | 1.3374 | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/products/backup_ |
| batch_scheduler_transition_spec_v4 | 0.0 | 422.975 | 0.130893 | 0.8788 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| certificate_rotation_readiness_spec_v4 | 0.0 | 201.153 | 0.03219 | 0.2161 | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line |
| edge_fleet_rollout_spec_v4 | 0.0 | 215.164 | 0.027674 | 0.1858 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| identity_federation_transition_spec_v4 | 0.0 | 421.163 | 0.132859 | 0.8920 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| network_policy_convergence_spec_v4 | 0.0 | 203.279 | 0.030426 | 0.2043 | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line |
| observability_retention_upgrade_spec_v4 | 0.0 | 201.271 | 0.029498 | 0.1980 | {"status": "failed", "reason": "local execution failed: MATERIALIZED 18\n Traceback (most recent call last):\n  File \"/app/check.py\", line |
| payment_settlement_reconciliation_spec_v4 | 0.0 | 188.613 | 0.029268 | 0.1965 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| regional_failover_readiness_spec_v4 | 0.0 | 197.718 | 0.033299 | 0.2236 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| search_index_rebuild_spec_v4 | 0.0 | 184.199 | 0.02939 | 0.1973 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| storage_tiering_migration_spec_v4 | 0.0 | 461.773 | 0.172558 | 1.1585 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| streaming_checkpoint_recovery_spec_v4 | 1.0 | 770.194 | 0.161887 | 1.0869 | {"entry": "context8/streaming_checkpoint_recovery_spec_v4", "status": "passed", "output_count": 5, "api_cases": 19, "protected_file_count":  |
| tenant_quota_rebalance_spec_v4 | 0.0 | 452.146 | 0.12856 | 0.8631 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |
| warehouse_cutover_assurance_spec_v4 | 0.0 | 190.077 | 0.038089 | 0.2557 | {"status": "failed", "reason": "local execution failed:  Traceback (most recent call last):\n  File \"/app/check.py\", line 23, in <module>\ |

## LATTE 原生 (`latte-native`)

- 任务数：16
- Reward 1：0
- ACC：0.00%
- E2E 平均：394.0s（6.57 min）
- Agent 平均：376.3s
- 成本：$3.7580 / ¥25.2302
- missing cost：12
- 有工具并发 trial：0 / 16；最大并发工具：not observed

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 0.0 | 37.859 |  |  | NonZeroAgentExitCodeError |
| artifact_provenance_release_spec_v4 | 0.0 | 45.091 |  |  | NonZeroAgentExitCodeError |
| backup_restore_certification_spec_v4 | 0.0 | 1516.985 | 1.383565 | 9.289 | NonZeroAgentExitCodeError |
| batch_scheduler_transition_spec_v4 | 0.0 | 63.351 |  |  | NonZeroAgentExitCodeError |
| certificate_rotation_readiness_spec_v4 | 0.0 | 46.2 |  |  | NonZeroAgentExitCodeError |
| edge_fleet_rollout_spec_v4 | 0.0 | 129.338 |  |  | NonZeroAgentExitCodeError |
| identity_federation_transition_spec_v4 | 0.0 | 34.017 |  |  | NonZeroAgentExitCodeError |
| network_policy_convergence_spec_v4 | 0.0 | 57.488 |  |  | NonZeroAgentExitCodeError |
| observability_retention_upgrade_spec_v4 | 0.0 | 1506.334 | 1.034337 | 6.9443 | NonZeroAgentExitCodeError |
| payment_settlement_reconciliation_spec_v4 | 0.0 | 37.527 |  |  | NonZeroAgentExitCodeError |
| regional_failover_readiness_spec_v4 | 0.0 | 82.762 |  |  | NonZeroAgentExitCodeError |
| search_index_rebuild_spec_v4 | 0.0 | 1353.691 | 0.915773 | 6.1483 | NonZeroAgentExitCodeError |
| storage_tiering_migration_spec_v4 | 0.0 | 67.18 |  |  | NonZeroAgentExitCodeError |
| streaming_checkpoint_recovery_spec_v4 | 0.0 | 37.184 |  |  | NonZeroAgentExitCodeError |
| tenant_quota_rebalance_spec_v4 | 0.0 | 1242.709 | 0.424288 | 2.8486 | NonZeroAgentExitCodeError |
| warehouse_cutover_assurance_spec_v4 | 0.0 | 45.933 |  |  | NonZeroAgentExitCodeError |

## LATTE 注入提示 (`latte-injected`)

- 任务数：16
- Reward 1：0
- ACC：0.00%
- E2E 平均：1347.6s（22.46 min）
- Agent 平均：1331.0s
- 成本：$14.5883 / ¥97.9430
- missing cost：0
- 有工具并发 trial：0 / 16；最大并发工具：not observed

| 任务 | Reward | E2E (s) | Cost USD | Cost CNY | 主要异常/verifier |
|---|---:|---:|---:|---:|---|
| api_deprecation_campaign_spec_v4 | 0.0 | 1790.393 | 0.797915 | 5.357 | NonZeroAgentExitCodeError |
| artifact_provenance_release_spec_v4 | 0.0 | 1252.905 | 1.024269 | 6.8767 | NonZeroAgentExitCodeError |
| backup_restore_certification_spec_v4 | 0.0 | 1277.261 | 0.906112 | 6.0835 | NonZeroAgentExitCodeError |
| batch_scheduler_transition_spec_v4 | 0.0 | 1917.692 | 1.1649 | 7.8209 | NonZeroAgentExitCodeError |
| certificate_rotation_readiness_spec_v4 | 0.0 | 1239.797 | 0.86627 | 5.816 | NonZeroAgentExitCodeError |
| edge_fleet_rollout_spec_v4 | 0.0 | 1650.262 | 0.836545 | 5.6164 | NonZeroAgentExitCodeError |
| identity_federation_transition_spec_v4 | 0.0 | 879.596 | 0.705024 | 4.7334 | NonZeroAgentExitCodeError |
| network_policy_convergence_spec_v4 | 0.0 | 975.604 | 0.697002 | 4.6795 | NonZeroAgentExitCodeError |
| observability_retention_upgrade_spec_v4 | 0.0 | 1112.206 | 0.582628 | 3.9116 | NonZeroAgentExitCodeError |
| payment_settlement_reconciliation_spec_v4 | 0.0 | 1376.562 | 0.78051 | 5.2402 | NonZeroAgentExitCodeError |
| regional_failover_readiness_spec_v4 | 0.0 | 1398.573 | 1.346084 | 9.0373 | NonZeroAgentExitCodeError |
| search_index_rebuild_spec_v4 | 0.0 | 1045.067 | 0.68245 | 4.5818 | NonZeroAgentExitCodeError |
| storage_tiering_migration_spec_v4 | 0.0 | 1367.697 | 1.421276 | 9.5422 | NonZeroAgentExitCodeError |
| streaming_checkpoint_recovery_spec_v4 | 0.0 | 1423.08 | 0.707292 | 4.7486 | NonZeroAgentExitCodeError |
| tenant_quota_rebalance_spec_v4 | 0.0 | 1403.825 | 0.663617 | 4.4554 | NonZeroAgentExitCodeError |
| warehouse_cutover_assurance_spec_v4 | 0.0 | 1451.209 | 1.406433 | 9.4425 | NonZeroAgentExitCodeError |

## 说明

- Codex 有 3 个 success trial 因 `max_output_tokens` / `turn.completed` 缺失，成本为 missing。
- LATTE 两种版本均未通过外部 verifier，Reward 1 为 0。
- LATTE native 有 12 个 trial 没有可读的 `latte_result`，token/cost 记为 missing。
- 工具并发不等于多 Agent 并行。
