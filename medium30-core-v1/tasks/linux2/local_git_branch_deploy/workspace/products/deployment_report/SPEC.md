# deployment_report

调用公开runtime.run_deploy(hook,routes,batches)或等价本地Git流程。batches每批包含待提交branch和完整files快照，需真实git push触发hook。返回 {files:{部署根下相对文件路径:UTF8内容}}。只测试有效提交和本地正常push，不测失败回滚/网络。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
