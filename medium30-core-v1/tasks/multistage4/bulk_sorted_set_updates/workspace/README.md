# N14 批量有序集合的累加与结果回填

批量更新多个集合成员的分数，同时按原操作顺序返回每次更新后的分数。

## 本版输入与业务范围

采用内存后端与 SQLite 后端的可见适配器；标准输入合法增量，不要求真实 Redis/MongoDB 或并发写入。

- `stages/operation_groups`：initial 是 {set_key:{member:整数分数}}；operations 是 [{key,member,delta:整数}]。按 (key,member) 分组并按键/成员字典序返回列表，每组为 {key,member,initial:原分数或0,operations:[{index:原始0基位置,delta}]}，保留组内原顺序。
- `stages/group_folds`：独立计算各组有序前缀和。返回列表 [{key,member,final:最终分数,results:[{index,score:本次操作后的分数}]}]，组顺序不变。
- `stages/bulk_result`：合并分组结果。返回 {scores:[按操作原位置的分数],sets:保留未操作成员的最终集合字典}。同一成员多次增分不可用最终值回填先前操作。count 等于操作数。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
