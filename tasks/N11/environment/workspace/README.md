# N11 零块保形的分块矩阵连乘（盲编排版）

## 业务范围

用有形状的零块和小整数稠密块代替完整符号系统；至少覆盖连续三次乘法。

- `engines/squared`：计算 B²，返回同分块结构；每个块仍含 rows/cols。全零块 data=null，其他块 data为整数二维列表。不得折叠成无形状标量0。
- `engines/cubed`：消费 B² 再乘 B，返回 {layout:输入layout,blocks:B³的有形状分块矩阵}；使用与 squared相同零块表示。
- `engines/block_layout`：matrix是二维块列表，每块 {rows,cols,data:整数二维列表或null}，null表示有形状的零矩阵。相同块行的rows一致，相同块列的cols一致；总体为方阵且块行列分割相同。返回 {row_sizes,col_sizes}。

## 实现与交付契约

完成各组件engine.py和项目入口run_all.py，可添加私有源码辅助模块。各SPEC与contract给出原业务算法、输入文件绑定、输出路径及接口；runtime.py仅提供通用加载、导入和落盘工具。

delivery.json是无序交付清单：component_outputs映射每个组件名与JSON产物路径，result_file指定最终业务结果文件。源码和清单的枚举位置不表示执行顺序。自行组织组件的实现和执行策略。

`python3 run_all.py`须从当前inputs/request.json生成全部组件和额外交付物，并写outputs/final_report.json：{"task":"N11","results":{组件名:对应组件JSON值,...},"result":result_file中的JSON值}。
`python3 check.py`执行你的入口并检查公开例子。正式验收会删除outputs后用新的合法业务输入重建；实现应保存在源码目录。engine.py中的transform、load_payload、build_component仍遵守原SPEC，build_component须能在只提供其绑定输入的干净目录独立工作。

README、SPEC、contract、输入、delivery.json、runtime.py、check.py和公开期望均受保护。run_all.py为可修改入口。评分沿用547单元中的原题注册清单，分别报告公开、核心转换、严格通过和Reward；单题上限2，50%验收完成分加50%严格完整交付奖励。调度策略不另加计分单元，未注册的通用稳健性不计分。
