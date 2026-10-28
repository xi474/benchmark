# 14. 备份恢复认证

任务：`linux2/backup_restore_certification`；[任务说明](../../tasks/linux2/backup_restore_certification/TASK.md) · [工作区说明](../../tasks/linux2/backup_restore_certification/workspace/README.md)。

核心组件 **3**；执行节点 **6**；最大独立宽度 **2**；最早分层 **1 → 2 → 1 → 1 → 1**。

![备份恢复认证组件执行DAG](backup_restore_certification.svg)

[PNG](backup_restore_certification.png) · [SVG](backup_restore_certification.svg) · [Mermaid 源码](backup_restore_certification.mmd) · [完整边表与契约摘要](backup_restore_certification.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["backup_graph<br/>恢复点与备份链成本优化"]:::component
  n1["journal_restore<br/>连续 LSN 与原子事务重放"]:::component
  n2["backup_windows<br/>快照与日志恢复一致性核验"]:::component
  n3[["materialize.py<br/>校验边界并生成 inputs / products"]]:::materialize
  n4["integrate.py<br/>读取全部 3 个组件产物"]:::integration
  n5["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n2
  n0 --> n4
  n1 --> n2
  n1 --> n4
  n2 --> n4
  n3 --> n0
  n3 --> n1
  n3 --> n2
  n4 --> n5
  input0[/"inputs/backup_graph.json"/]:::input
  n3 -.-> input0
  input0 -.-> n0
  input1[/"inputs/journal_restore.json"/]:::input
  n3 -.-> input1
  input1 -.-> n1
  input2[/"inputs/backup_windows.json"/]:::input
  n3 -.-> input2
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `products/backup_graph`：恢复点与备份链成本优化；输入 `inputs/backup_graph.json`；输出 `outputs/backup_graph.json`。

- `products/journal_restore`：连续 LSN 与原子事务重放；输入 `inputs/journal_restore.json`；输出 `outputs/journal_restore.json`。

- `products/backup_windows`：快照与日志恢复一致性核验；输入 `inputs/backup_windows.json`、`outputs/backup_graph.json`、`outputs/journal_restore.json`；输出 `outputs/backup_windows.json`。

## 边的校验说明

完整执行边 9 条；传递约简后 6 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
