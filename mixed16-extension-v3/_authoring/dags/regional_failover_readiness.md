# 01. 跨区域故障切换

任务：`multistage4/regional_failover_readiness`；[任务说明](../../tasks/multistage4/regional_failover_readiness/TASK.md) · [工作区说明](../../tasks/multistage4/regional_failover_readiness/workspace/README.md)。

核心组件 **6**；执行节点 **9**；最大独立宽度 **3**；最早分层 **3 → 1 → 3 → 1 → 1**。

![跨区域故障切换组件执行DAG](regional_failover_readiness.svg)

[PNG](regional_failover_readiness.png) · [SVG](regional_failover_readiness.svg) · [Mermaid 源码](regional_failover_readiness.mmd) · [完整边表与契约摘要](regional_failover_readiness.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["replication<br/>延迟证据与修订去重"]:::component
  n1["failover<br/>失败率证据与修订去重"]:::component
  n2["snapshots<br/>完整性证据与修订去重"]:::component
  n3["risk_queue<br/>阈值筛选与风险排序"]:::component
  n4["duty_queue<br/>审核负载分配"]:::component
  n5["recovery_waves<br/>修复波次与关键路径"]:::component
  n6["integrate.py domains<br/>合并全部 domains 证据"]:::integration
  n7["integrate.py<br/>读取全部 6 个组件产物"]:::integration
  n8["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n6
  n0 --> n7
  n1 --> n6
  n1 --> n7
  n2 --> n6
  n2 --> n7
  n3 --> n7
  n4 --> n7
  n5 --> n7
  n6 --> n3
  n6 --> n4
  n6 --> n5
  n7 --> n8
  input0[/"inputs/replication.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/failover.json"/]:::input
  input1 -.-> n1
  input2[/"inputs/snapshots.json"/]:::input
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `domains/replication`：延迟证据与修订去重；输入 `inputs/replication.json`；输出 `outputs/replication.json`。

- `domains/failover`：失败率证据与修订去重；输入 `inputs/failover.json`；输出 `outputs/failover.json`。

- `domains/snapshots`：完整性证据与修订去重；输入 `inputs/snapshots.json`；输出 `outputs/snapshots.json`。

- `views/risk_queue`：阈值筛选与风险排序；输入 `outputs/domain_core.json`；输出 `outputs/risk_queue.json`。

- `views/duty_queue`：审核负载分配；输入 `outputs/domain_core.json`；输出 `outputs/duty_queue.json`。

- `views/recovery_waves`：修复波次与关键路径；输入 `outputs/domain_core.json`；输出 `outputs/recovery_waves.json`。

## 边的校验说明

完整执行边 13 条；传递约简后 10 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
