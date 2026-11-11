# N11 零块保形的分块矩阵连乘

对小型分块矩阵完成多次乘法，保留零块的行列形状，保证中间结果还能继续参与运算。

## 本版输入与业务范围

用有形状的零块和小整数稠密块代替完整符号系统；至少覆盖连续三次乘法。

- `engines/block_layout`：matrix是二维块列表，每块 {rows,cols,data:整数二维列表或null}，null表示有形状的零矩阵。相同块行的rows一致，相同块列的cols一致；总体为方阵且块行列分割相同。返回 {row_sizes,col_sizes}。
- `engines/squared`：计算 B²，返回同分块结构；每个块仍含 rows/cols。全零块 data=null，其他块 data为整数二维列表。不得折叠成无形状标量0。
- `engines/cubed`：消费 B² 再乘 B，返回 {layout:输入layout,blocks:B³的有形状分块矩阵}；使用与 squared相同零块表示。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
