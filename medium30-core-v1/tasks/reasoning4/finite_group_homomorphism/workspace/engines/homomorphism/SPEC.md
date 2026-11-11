# homomorphism

检查 generators[i]→images[i] 是否定义同态。返回 {valid:false,mapping:[]} 或 {valid:true,mapping:[{source:源置换,target:目标置换},...]}，mapping按源置换字典序。不同生成词到同一源元素必须得到同一像，包含逆元形成的关系。不是单独检查每个像为合法置换。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
