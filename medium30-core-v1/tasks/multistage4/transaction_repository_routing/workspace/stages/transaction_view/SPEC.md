# transaction_view

在本地SQLite执行有限脚本。事件 begin/commit；put={kind:'put',repo:'album'|'artist',id,name}；get={kind:'get',repo,id}。事务中put/get均走事务连接，事务外get走read、put走write；get返回对应name或null。初始数据initial={albums:[{id,name}],artists:[...]}。返回 {reads:[get结果],routes:[每个put/get的'transaction'|'read'|'write'],final:{albums:按id排序行,artists:按id排序行}}。只测顺序事务，无锁竞争/重试。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
