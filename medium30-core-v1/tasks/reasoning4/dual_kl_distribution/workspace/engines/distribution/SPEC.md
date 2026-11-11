# distribution

构造长度model.n的正概率向量列表，和误差<=1e-5；KL(P||U)及KL(U||P)分别与targets误差<=0.001，使用自然对数。返回概率列表，允许任意合法解。可用预装NumPy/SciPy标准求根；无需GPU或训练。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
