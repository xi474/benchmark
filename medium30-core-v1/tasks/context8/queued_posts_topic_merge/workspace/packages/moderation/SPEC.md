# moderation

顺序执行有限事件。post={kind:'post',id,tid,user}：豁免者直接published，否则入queue。merge={kind:'merge',sources:[活跃主题],target:另一活跃主题}：删除source主题并把所有待审/已发布帖子tid迁到target。approve={kind:'approve',id:待审post}：移到published。返回 {topics:排序活跃ID,queue:按id排序帖子,published:按id排序帖子}。不加入并发、撤销或失败重试。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
