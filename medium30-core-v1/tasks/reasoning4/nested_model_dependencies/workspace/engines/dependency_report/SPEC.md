# dependency_report

按 kind=parallel/serial 组合两个矩阵。返回 {matrix:依赖矩阵,input_count:列数,output_count:行数,separable:[bool,...]}。某输出恰好依赖一个输入，且没有其他输出依赖同一输入时才 separable=true。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
