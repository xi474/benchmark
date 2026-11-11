# variable_plan

dataset.variables 是 {name:{dims:[维度名],data:[整数],attrs:字段字典}}；swap 是单个 {旧维度:新坐标变量名}。生成变量计划 {name:{dims:替换后的维度列表,data:原数据,attrs:原attrs}}，所有结果可变元数据必须与输入隔离。输入是一维同长变量，目标坐标变量存在。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
