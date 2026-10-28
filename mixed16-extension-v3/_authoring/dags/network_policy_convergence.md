# 16. 网络策略收敛

任务：`linux2/network_policy_convergence`；[任务说明](../../tasks/linux2/network_policy_convergence/TASK.md) · [工作区说明](../../tasks/linux2/network_policy_convergence/workspace/README.md)。

核心组件 **3**；执行节点 **6**；最大独立宽度 **2**；最早分层 **1 → 2 → 1 → 1 → 1**。

![网络策略收敛组件执行DAG](network_policy_convergence.svg)

[PNG](network_policy_convergence.png) · [SVG](network_policy_convergence.svg) · [Mermaid 源码](network_policy_convergence.mmd) · [完整边表与契约摘要](network_policy_convergence.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["route_graph<br/>故障后的等价最短路径集"]:::component
  n1["firewall_policy<br/>时序连接状态防火墙"]:::component
  n2["network_traces<br/>路由与状态决策联合核验"]:::component
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
  input0[/"inputs/route_graph.json"/]:::input
  n3 -.-> input0
  input0 -.-> n0
  input1[/"inputs/firewall_policy.json"/]:::input
  n3 -.-> input1
  input1 -.-> n1
  input2[/"inputs/network_traces.json"/]:::input
  n3 -.-> input2
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `products/route_graph`：故障后的等价最短路径集；输入 `inputs/route_graph.json`；输出 `outputs/route_graph.json`。

- `products/firewall_policy`：时序连接状态防火墙；输入 `inputs/firewall_policy.json`；输出 `outputs/firewall_policy.json`。

- `products/network_traces`：路由与状态决策联合核验；输入 `inputs/network_traces.json`、`outputs/route_graph.json`、`outputs/firewall_policy.json`；输出 `outputs/network_traces.json`。

## 边的校验说明

完整执行边 9 条；传递约简后 6 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
