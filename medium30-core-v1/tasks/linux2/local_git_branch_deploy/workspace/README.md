# N25 本地 Git 双分支自动部署

搭建本地 bare 仓库和 post-receive hook，将 main/dev 的内容各自部署到对应目录。

## 本版输入与业务范围

移除SSH、HTTPS及3秒墙钟门槛；保留真实本地Git多ref接收hook与两个分支的部署隔离。

- `products/branch_routes`：返回路由映射独立副本，refs/heads/main与refs/heads/dev指向互不包含的相对部署目录。无SSH/Nginx/TLS。
- `products/deployment_hook`：返回Python post-receive业务脚本字符串，stdin每行old new ref；一次可有多行。GIT_DIR来自环境，MEDIUM30_DEPLOY_ROOT为部署根。对路由内非删除ref，把new commit树完整部署到对应目录，清除该分支旧文件但不影响另一分支；未路由ref忽略。提供的run_deploy负责创建仓库、安装Python启动shim及真实git push，脚本只需实现业务分派。允许任意正确脚本，不比脚本文本。
- `products/deployment_report`：调用公开runtime.run_deploy(hook,routes,batches)或等价本地Git流程。batches每批包含待提交branch和完整files快照，需真实git push触发hook。返回 {files:{部署根下相对文件路径:UTF8内容}}。只测试有效提交和本地正常push，不测失败回滚/网络。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
