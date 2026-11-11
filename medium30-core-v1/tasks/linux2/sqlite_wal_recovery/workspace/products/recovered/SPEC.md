# recovered

把真实基础库及还原WAL按同名.db/-wal放到临时目录，让SQLite恢复并查询。返回 {records:按id排序的全部记录,base_count:基础记录数,database:原base64库,wal:还原WAL的base64}。不能仅追加两个记录列表，WAL含旧行更新。组件封装写 outputs/recovery_snapshot.json，业务列表单独写 outputs/recovered.json，不得互相覆盖。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
