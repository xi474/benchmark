# template_dependencies

templates={模板ID:文本}，只分析 {{ Python兼容表达式 }}；支持 conf 属性、静态字符串下标与算术表达式，不执行模板。提取conf开头访问链，把下标转点号；以options中最长合法前缀作为配置项，忽略notconf及模板普通文本。输入每个conf链至少有一个合法前缀。返回 {模板ID:排序唯一配置键列表}。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
