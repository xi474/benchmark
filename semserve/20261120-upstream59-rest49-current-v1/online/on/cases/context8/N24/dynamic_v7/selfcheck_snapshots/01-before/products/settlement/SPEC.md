# settlement

顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。成功时买方余额减金额、卖方增加、owner改买方，向 journal 追加 book4+amount10+seller4+buyer4；不符所有权时三类文件不变。返回 {accounts:重编码定长串,books:重编码定长串,journal:累计交易串,statuses:['accepted'|'rejected',...]}。保持原记录顺序，姓名/书名填充20位，数值填充10位。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
