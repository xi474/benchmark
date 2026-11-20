# cleaned_repo

先确认已恢复标记，再删除仓库中的该标记，包括reflog和不可达对象；保留普通工作区内容与正常提交说明。返回 {bundle:清理后完整仓库tar.gz的base64,files:{普通相对路径:SHA256},messages:[git log --format=%s按新到旧]}。允许任意语义正确仓库重打包，不比tar字节。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
