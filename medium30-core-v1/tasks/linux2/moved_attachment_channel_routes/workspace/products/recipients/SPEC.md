# recipients

people=[{id,teacher:是否现任或曾任历史教师,former,country,pilot:是否曾任飞行员,messages:是否支持Messages}]。目标邮件收件人为email_sender与唯一country=RU且pilot=true联系人之并集。教师排除self后按messages分区。返回 {target_email:排序ID,messages:排序教师ID,fallback_email:排序教师ID}；former不排除教师。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
