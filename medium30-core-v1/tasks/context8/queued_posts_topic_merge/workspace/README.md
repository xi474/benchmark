# N13 主题合并后的待审帖子归属

执行有限的发帖、主题合并与审批序列，使待审帖子始终归属有效主题，豁免组仍可直接发帖。

## 本版输入与业务范围

保留主题重定向、队列归属更新和组豁免；用离线状态表与顺序事件替代论坛、数据库和 Web UI。

- `packages/exempt_users`：memberships={用户ID:[组名]}；返回属于任一豁免组的用户ID，按字典序。
- `packages/initial_queue`：将初始待审 posts=[{id,tid,user}] 独立拷贝，按post ID排序返回。所有引用为已知主题。
- `packages/moderation`：顺序执行有限事件。post={kind:'post',id,tid,user}：豁免者直接published，否则入queue。merge={kind:'merge',sources:[活跃主题],target:另一活跃主题}：删除source主题并把所有待审/已发布帖子tid迁到target。approve={kind:'approve',id:待审post}：移到published。返回 {topics:排序活跃ID,queue:按id排序帖子,published:按id排序帖子}。不加入并发、撤销或失败重试。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
