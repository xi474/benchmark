# 10. 身份联邦迁移

任务：`context8/identity_federation_transition`；[任务说明](../../tasks/context8/identity_federation_transition/TASK.md) · [工作区说明](../../tasks/context8/identity_federation_transition/workspace/README.md)。

核心组件 **3**；执行节点 **5**；最大独立宽度 **2**；最早分层 **2 → 1 → 1 → 1**。

![身份联邦迁移组件执行DAG](identity_federation_transition.svg)

[PNG](identity_federation_transition.png) · [SVG](identity_federation_transition.svg) · [Mermaid 源码](identity_federation_transition.mmd) · [完整边表与契约摘要](identity_federation_transition.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["claims<br/>声明模式兼容判定"]:::component
  n1["sessions<br/>令牌轮换与撤销传播"]:::component
  n2["authorization<br/>组继承闭包与联合授权"]:::component
  n3["integrate.py<br/>读取全部 3 个组件产物"]:::integration
  n4["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n2
  n0 --> n3
  n1 --> n2
  n1 --> n3
  n2 --> n3
  n3 --> n4
  input0[/"inputs/claims.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/sessions.json"/]:::input
  input1 -.-> n1
  input2[/"inputs/authorization.json"/]:::input
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `claims`：声明模式兼容判定；输入 `inputs/claims.json`；输出 `outputs/claims.json`。

- `sessions`：令牌轮换与撤销传播；输入 `inputs/sessions.json`；输出 `outputs/sessions.json`。

- `authorization`：组继承闭包与联合授权；输入 `inputs/authorization.json`、`outputs/claims.json`、`outputs/sessions.json`；输出 `outputs/authorization.json`。

## 边的校验说明

完整执行边 6 条；传递约简后 4 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
