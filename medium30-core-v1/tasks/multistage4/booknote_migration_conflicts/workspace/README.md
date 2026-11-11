# N16 书目迁移中两种冲突策略

迁移 work_id 时，让书评保留所有冲突记录，而书架沿用删除旧项策略，返回准确的操作统计。

## 本版输入与业务范围

用两个小表和 SQLite 实现，保留每种表的冲突契约与固定三项统计；兼容异常类型由可见适配层提供，不安装 PostgreSQL。

- `stages/notes`：rows={work_id:笔记文本}。old存在；若new已存在且不同于old，保持所有笔记，统计 {rows_changed:0,rows_deleted:0,failed_deletes:1}。new不存在则迁移键，changed=1；old==new无操作。返回 {rows:更新字典,stats:上述三个计数}。
- `stages/shelves`：与notes使用相同输入结构，但发生目标键冲突时保留目标、删除old，stats={rows_changed:0,rows_deleted:1,failed_deletes:0}。无冲突则迁移。
- `stages/migration_report`：返回 {notes:notes结果,shelves:shelves结果}。不得给两类表统一应用delete-on-conflict。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
