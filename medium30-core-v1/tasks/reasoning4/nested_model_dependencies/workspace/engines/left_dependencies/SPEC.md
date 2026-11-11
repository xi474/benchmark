# left_dependencies

输入 model 是叶子 {kind:'leaf',matrix:[[0或1,...],...]}，或 {kind:'parallel'|'serial',left:模型,right:模型}。矩阵行对应输出，列对应输入。parallel 使用块对角；serial 表示先 left 后 right，结果是 right×left 的布尔乘积。返回依赖矩阵（0/1 的二维列表）。所有维度合法、矩阵非空；树深≤6，输入输出维度≤12。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
