# moved_document

Files应用的虚拟快照files={相对路径:不透明文件字节的base64}，夹具为可打开的有效xlsx。移动source到destination，目标父目录可创建。返回 {files:移动后快照,attachment:{path:destination,content:原base64,sha256:解码后实际文件字节摘要}}。source存在、destination未占用。只保留字节，不解析xlsx内部。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
