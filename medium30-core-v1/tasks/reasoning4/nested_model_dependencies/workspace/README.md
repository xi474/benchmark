# N01 嵌套模型的输入输出依赖矩阵

根据小型模型表达式树，计算每个输出依赖哪些输入，保持并联嵌套前后的依赖一致。

## 本版输入与业务范围

用声明式模型树替代 Astropy 对象；支持叶子依赖、并联与串联，以布尔矩阵完成组合，并输出可分离性报告。树和矩阵均为小规模。

- `engines/left_dependencies`：输入 model 是叶子 {kind:'leaf',matrix:[[0或1,...],...]}，或 {kind:'parallel'|'serial',left:模型,right:模型}。矩阵行对应输出，列对应输入。parallel 使用块对角；serial 表示先 left 后 right，结果是 right×left 的布尔乘积。返回依赖矩阵（0/1 的二维列表）。所有维度合法、矩阵非空；树深≤6，输入输出维度≤12。
- `engines/right_dependencies`：与 left_dependencies 相同的模型依赖规则，独立计算右子树。
- `engines/dependency_report`：按 kind=parallel/serial 组合两个矩阵。返回 {matrix:依赖矩阵,input_count:列数,output_count:行数,separable:[bool,...]}。某输出恰好依赖一个输入，且没有其他输出依赖同一输入时才 separable=true。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
