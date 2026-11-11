# member_plan

输入为受控虚拟 collection 根目录，nodes=[{path,kind:'file'|'dir'|'symlink',content或target}]，symlink相对所在目录解析。没有循环/悬空链接；外部文件内容由external_files以绝对虚拟路径给出，不读实际工作区外文件。规范化后落在/collection外的成员路径拒绝；内部链接保留为symlink，其相对linkname不展开；外部文件链接复制内容为普通file。返回 {members:按name排序[{name,type,content(仅file),linkname(仅symlink)}],rejected:排序拒绝path}。目录没有多余字段。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
