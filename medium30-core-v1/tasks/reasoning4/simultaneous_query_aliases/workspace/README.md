# N06 查询组合中的无碰撞别名重写

组合两棵简化查询树，分配无碰撞表别名，并同步重写 JOIN 和谓词引用。

## 本版输入与业务范围

保留查询组合、别名身份和引用一致性；用限定查询 AST 与小型关系表替代完整 ORM。

- `engines/symbol_tables`：left/right 是 {tables:{alias:表名},clauses:[{alias,field,value}]}；每个 clause.alias 都在对应 tables 内。返回 {left:排序别名列表,right:排序别名列表}。
- `engines/rename_map`：为右查询的每个原别名按字典序分配新别名 T0,T1,...，跳过左右原别名及已分配名称。返回 {原右别名:新别名}。此公开命名规则用于稳定输出；替换必须同时进行，不能串行替换导致二次改名。
- `engines/combined_query`：返回 {tables:左表映射与重命名后右表映射,branches:[左clauses,按原映射同时改名的右clauses]}。保留每个 clause 的 field/value 与原顺序，两分支表示 OR，不把字符串 value 内的别名文本当引用改写。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
