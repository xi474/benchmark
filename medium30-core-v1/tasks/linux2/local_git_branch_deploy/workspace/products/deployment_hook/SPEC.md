# deployment_hook

返回Python post-receive业务脚本字符串，stdin每行old new ref；一次可有多行。GIT_DIR来自环境，MEDIUM30_DEPLOY_ROOT为部署根。对路由内非删除ref，把new commit树完整部署到对应目录，清除该分支旧文件但不影响另一分支；未路由ref忽略。提供的run_deploy负责创建仓库、安装Python启动shim及真实git push，脚本只需实现业务分派。允许任意正确脚本，不比脚本文本。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
