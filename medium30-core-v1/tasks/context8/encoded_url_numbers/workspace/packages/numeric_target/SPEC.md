# numeric_target

依 host,port,path,query,anchor 的 URL 顺序，在给定 segments 中找到最后一个可修改连续 ASCII 数字串。合法 %XX 三字符内的数字必须屏蔽；其后的普通数字可修改。返回 {segment,start,end,text}，start/end 是对应原始段的0基半开跨度。输入保证存在可选数字。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
