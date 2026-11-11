# operation_groups

initial 是 {set_key:{member:整数分数}}；operations 是 [{key,member,delta:整数}]。按 (key,member) 分组并按键/成员字典序返回列表，每组为 {key,member,initial:原分数或0,operations:[{index:原始0基位置,delta}]}，保留组内原顺序。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
