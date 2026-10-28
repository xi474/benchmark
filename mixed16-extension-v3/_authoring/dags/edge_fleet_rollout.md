# 05. 边缘设备灰度发布

任务：`reasoning4/edge_fleet_rollout`；[任务说明](../../tasks/reasoning4/edge_fleet_rollout/TASK.md) · [工作区说明](../../tasks/reasoning4/edge_fleet_rollout/workspace/README.md)。

核心组件 **3**；执行节点 **5**；最大独立宽度 **2**；最早分层 **2 → 1 → 1 → 1**。

![边缘设备灰度发布组件执行DAG](edge_fleet_rollout.svg)

[PNG](edge_fleet_rollout.png) · [SVG](edge_fleet_rollout.svg) · [Mermaid 源码](edge_fleet_rollout.mmd) · [完整边表与契约摘要](edge_fleet_rollout.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["maintenance_windows<br/>加权区间选择"]:::component
  n1["crew_assignment<br/>技能与容量约束分配"]:::component
  n2["rollout_order<br/>依赖波次与关键路径"]:::component
  n3["integrate.py<br/>读取全部 3 个组件产物"]:::integration
  n4["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n3
  n1 --> n2
  n1 --> n3
  n2 --> n3
  n3 --> n4
  input0[/"inputs/maintenance_windows.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/crew_assignment.json"/]:::input
  input1 -.-> n1
  input2[/"inputs/rollout_order.json"/]:::input
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `engines/maintenance_windows`：加权区间选择；输入 `inputs/maintenance_windows.json`；输出 `outputs/maintenance_windows.json`。

- `engines/crew_assignment`：技能与容量约束分配；输入 `inputs/crew_assignment.json`；输出 `outputs/crew_assignment.json`。

- `engines/rollout_order`：依赖波次与关键路径；输入 `inputs/rollout_order.json`、`outputs/crew_assignment.json`；输出 `outputs/rollout_order.json`。

## 边的校验说明

完整执行边 5 条；传递约简后 4 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
