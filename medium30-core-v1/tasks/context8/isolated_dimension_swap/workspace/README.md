# N02 维度替换后的元数据隔离

实现轻量数据集的维度替换，生成正确的新坐标和变量描述，同时保持原数据集不变。

## 本版输入与业务范围

保留变量→索引变量转换与复制隔离；以小型 Python 对象代替完整 xarray，只覆盖公开的替换操作和必要元数据。

- `packages/variable_plan`：dataset.variables 是 {name:{dims:[维度名],data:[整数],attrs:字段字典}}；swap 是单个 {旧维度:新坐标变量名}。生成变量计划 {name:{dims:替换后的维度列表,data:原数据,attrs:原attrs}}，所有结果可变元数据必须与输入隔离。输入是一维同长变量，目标坐标变量存在。
- `packages/coordinate_plan`：返回 {coords:把 swap 的目标变量加入原 coords 后排序去重,indexes:{新坐标名:目标变量的数据}}。
- `packages/new_dataset`：返回新 {variables,coords,indexes}，对象不得通过可变 dims/attrs/coords/indexes 别名修改 payload。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
