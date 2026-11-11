# threshold_actions

仅统计group:new中members发出的0<=at<window消息，每人只计一次，按(at,id)处理。首次达到threshold时触发一次；之后不再追加订车。返回 {group:输入group,trigger_at:逻辑秒或null,ride:null或{at,pickup:'21:30',vehicle:'van',from:'home',to:'Tegnergatan 8'},notice:null或{at,meet:'20:00'},deleted:触发时evening否则[]}。未达到阈值是正常业务分支。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
