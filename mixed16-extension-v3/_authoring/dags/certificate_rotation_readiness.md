# 13. 证书轮换准备

任务：`linux2/certificate_rotation_readiness`；[任务说明](../../tasks/linux2/certificate_rotation_readiness/TASK.md) · [工作区说明](../../tasks/linux2/certificate_rotation_readiness/workspace/README.md)。

核心组件 **3**；执行节点 **6**；最大独立宽度 **2**；最早分层 **1 → 2 → 1 → 1 → 1**。

![证书轮换准备组件执行DAG](certificate_rotation_readiness.svg)

[PNG](certificate_rotation_readiness.png) · [SVG](certificate_rotation_readiness.svg) · [Mermaid 源码](certificate_rotation_readiness.mmd) · [完整边表与契约摘要](certificate_rotation_readiness.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["trust_graph<br/>最宽有效信任路径"]:::component
  n1["trust_policy<br/>通配策略优先级判定"]:::component
  n2["renewal_windows<br/>信任与策略约束的轮换覆盖"]:::component
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
  input0[/"inputs/trust_graph.json"/]:::input
  n3 -.-> input0
  input0 -.-> n0
  input1[/"inputs/trust_policy.json"/]:::input
  n3 -.-> input1
  input1 -.-> n1
  input2[/"inputs/renewal_windows.json"/]:::input
  n3 -.-> input2
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `products/trust_graph`：最宽有效信任路径；输入 `inputs/trust_graph.json`；输出 `outputs/trust_graph.json`。

- `products/trust_policy`：通配策略优先级判定；输入 `inputs/trust_policy.json`；输出 `outputs/trust_policy.json`。

- `products/renewal_windows`：信任与策略约束的轮换覆盖；输入 `inputs/renewal_windows.json`、`outputs/trust_graph.json`、`outputs/trust_policy.json`；输出 `outputs/renewal_windows.json`。

## 边的校验说明

完整执行边 9 条；传递约简后 6 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
