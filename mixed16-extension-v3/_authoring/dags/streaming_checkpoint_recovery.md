# 11. 流处理检查点恢复

任务：`context8/streaming_checkpoint_recovery`；[任务说明](../../tasks/context8/streaming_checkpoint_recovery/TASK.md) · [工作区说明](../../tasks/context8/streaming_checkpoint_recovery/workspace/README.md)。

核心组件 **3**；执行节点 **5**；最大独立宽度 **2**；最早分层 **2 → 1 → 1 → 1**。

![流处理检查点恢复组件执行DAG](streaming_checkpoint_recovery.svg)

[PNG](streaming_checkpoint_recovery.png) · [SVG](streaming_checkpoint_recovery.svg) · [Mermaid 源码](streaming_checkpoint_recovery.mmd) · [完整边表与契约摘要](streaming_checkpoint_recovery.json) · [图集目录](README.md)

## 完整依赖图（含输入文件）

虚线连接输入文件，实线为全部直接执行依赖；因此比上方传递约简图多出冗余但真实的读取边。

```mermaid
flowchart TD
  n0["event_codec<br/>新旧事件编码兼容"]:::component
  n1["checkpoint_restore<br/>连续确认偏移恢复"]:::component
  n2["diagnostic_logs<br/>混合格式日志脱敏"]:::component
  n3["integrate.py<br/>读取全部 3 个组件产物"]:::integration
  n4["final_report.py<br/>报告摘要与关注项"]:::report
  n0 --> n1
  n0 --> n3
  n1 --> n3
  n2 --> n3
  n3 --> n4
  input0[/"inputs/event_codec.json"/]:::input
  input0 -.-> n0
  input1[/"inputs/diagnostic_logs.json"/]:::input
  input1 -.-> n2
  classDef component fill:#eff6ff,stroke:#2563eb,color:#172033
  classDef materialize fill:#fff7ed,stroke:#c2410c,color:#172033
  classDef integration fill:#f5f3ff,stroke:#7c3aed,color:#172033
  classDef report fill:#ecfdf5,stroke:#047857,color:#172033
  classDef input fill:#f8fafc,stroke:#94a3b8,color:#475569,stroke-dasharray:4 3
```

## 组件与输入接口

- `event_codec`：新旧事件编码兼容；输入 `inputs/event_codec.json`；输出 `outputs/event_codec.json`。

- `checkpoint_restore`：连续确认偏移恢复；输入 `outputs/event_codec.json`；输出 `outputs/checkpoint_restore.json`。

- `diagnostic_logs`：混合格式日志脱敏；输入 `inputs/diagnostic_logs.json`；输出 `outputs/diagnostic_logs.json`。

## 边的校验说明

完整执行边 5 条；传递约简后 4 条。两者传递闭包完全相同，所有执行节点都能到达最终报告。

本图只描述逻辑组件与文件接口，不要求代理按固定调度器运行；实际实现可以在满足依赖的前提下串行或并行。
