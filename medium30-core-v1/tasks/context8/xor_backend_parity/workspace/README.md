# N04 跨 SQL 后端的 XOR 奇偶语义

把同一布尔谓词树分别编译为原生 XOR 和无 XOR 后端可执行的表达式，使查询选择一致。

## 本版输入与业务范围

保留原生/回退两种后端语义，限定小型布尔 AST 与非空布尔字段；使用 SQLite 执行回退表达式，不需要真实数据库服务器。

- `packages/native_values`：ast 为字段名字符串，或 {op:'and'|'or'|'xor',args:[AST,...]}。args 非空，字段为非空布尔值。按布尔逻辑计算每行真假，xor 为真项数的奇偶性。返回 [bool,...]，按 rows 原顺序。
- `packages/fallback_values`：为不支持原生 XOR 的 SQLite 编译参数表达式（字段写成 :字段），实际执行每行。返回 {sql:可用于 SELECT(expression) 的SQLite表达式,values:[bool,...]}。允许任何语义等价表达式，不要求固定SQL文本。xor 的 fallback 必须保持奇偶性。
- `packages/query_result`：若两后端 values 一致，返回 {values:真假列表,selected_ids:按输入顺序选中行ID}。消费实际后端结果，不使用固定答案。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
