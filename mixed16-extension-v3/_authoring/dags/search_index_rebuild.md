# 12. 搜索索引重建

任务：`context8/search_index_rebuild`；[任务说明](../../tasks/context8/search_index_rebuild/TASK.md) · [工作区说明](../../tasks/context8/search_index_rebuild/workspace/README.md)。

核心组件 **3**；执行节点 **5**；最大独立宽度 **2**；最早分层 **2 → 1 → 1 → 1**。

![搜索索引重建组件执行DAG](search_index_rebuild.svg)

[PNG](search_index_rebuild.png) · [SVG](search_index_rebuild.svg) · [Mermaid 源码](search_index_rebuild.mmd) · [完整边表与契约摘要](search_index_rebuild.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["mapping_compat<br/>重命名图与模式迁移"]:::component
  n1["shard_replay<br/>分片缺口与墓碑恢复"]:::component
  n2["cutover_plan<br/>预算与副本仲裁优化"]:::component
  n3["integrate.py<br/>读取全部 3 个组件产物"]:::integration
  n4["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n2
  n0 --> n3
  n1 --> n2
  n1 --> n3
  n2 --> n3
  n3 --> n4
  input0[/"inputs/mapping_compat.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/shard_replay.json"/]:::input
  input1 -.-> n1
  input2[/"inputs/cutover_plan.json"/]:::input
  input2 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `mapping_compat`：重命名图与模式迁移；输入 `inputs/mapping_compat.json`；输出 `outputs/mapping_compat.json`。

- `shard_replay`：分片缺口与墓碑恢复；输入 `inputs/shard_replay.json`；输出 `outputs/shard_replay.json`。

- `cutover_plan`：预算与副本仲裁优化；输入 `inputs/cutover_plan.json`、`outputs/mapping_compat.json`、`outputs/shard_replay.json`；输出 `outputs/cutover_plan.json`。

## 边的校验说明

完整执行边 6 条；传递约简后 4 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
