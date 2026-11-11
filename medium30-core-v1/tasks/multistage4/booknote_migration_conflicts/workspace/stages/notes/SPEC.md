# notes

rows={work_id:笔记文本}。old存在；若new已存在且不同于old，保持所有笔记，统计 {rows_changed:0,rows_deleted:0,failed_deletes:1}。new不存在则迁移键，changed=1；old==new无操作。返回 {rows:更新字典,stats:上述三个计数}。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
