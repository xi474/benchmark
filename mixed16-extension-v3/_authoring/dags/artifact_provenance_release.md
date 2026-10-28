# 03. 制品溯源发布

任务：`multistage4/artifact_provenance_release`；[任务说明](../../tasks/multistage4/artifact_provenance_release/TASK.md) · [工作区说明](../../tasks/multistage4/artifact_provenance_release/workspace/README.md)。

核心组件 **6**；执行节点 **8**；最大独立宽度 **3**；最早分层 **3 → 2 → 1 → 1 → 1**。

![制品溯源发布组件执行DAG](artifact_provenance_release.svg)

[PNG](artifact_provenance_release.png) · [SVG](artifact_provenance_release.svg) · [Mermaid 源码](artifact_provenance_release.mmd) · [完整边表与契约摘要](artifact_provenance_release.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["builds<br/>失败率证据与修订去重"]:::component
  n1["signatures<br/>完整性证据与修订去重"]:::component
  n2["scans<br/>延迟证据与修订去重"]:::component
  n3["release_risk<br/>阈值筛选与风险排序"]:::component
  n4["audit_assignment<br/>审核负载分配"]:::component
  n5["remediation_waves<br/>修复波次与关键路径"]:::component
  n6["integrate.py<br/>读取全部 6 个组件产物"]:::integration
  n7["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n3
  n0 --> n6
  n1 --> n3
  n1 --> n6
  n2 --> n4
  n2 --> n6
  n3 --> n5
  n3 --> n6
  n4 --> n5
  n4 --> n6
  n5 --> n6
  n6 --> n7
  input0[/"inputs/builds.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/signatures.json"/]:::input
  input1 -.-> n1
  input2[/"inputs/scans.json"/]:::input
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `domains/builds`：失败率证据与修订去重；输入 `inputs/builds.json`；输出 `outputs/builds.json`。

- `domains/signatures`：完整性证据与修订去重；输入 `inputs/signatures.json`；输出 `outputs/signatures.json`。

- `domains/scans`：延迟证据与修订去重；输入 `inputs/scans.json`；输出 `outputs/scans.json`。

- `views/release_risk`：阈值筛选与风险排序；输入 `outputs/builds.json`、`outputs/signatures.json`；输出 `outputs/release_risk.json`。

- `views/audit_assignment`：审核负载分配；输入 `outputs/scans.json`；输出 `outputs/audit_assignment.json`。

- `views/remediation_waves`：修复波次与关键路径；输入 `outputs/release_risk.json`、`outputs/audit_assignment.json`；输出 `outputs/remediation_waves.json`。

## 边的校验说明

完整执行边 12 条；传递约简后 7 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
