# N22 Git 遗失对象恢复与彻底清理

从本地测试仓库中恢复被重写历史遗失的合成标记，再清理仓库内相关对象，保留无关文件和提交说明。

## 本版输入与业务范围

输入以归档承载真实本地Git仓库。恢复与清理必须在可独立解包的仓库上成立；公开检查只公开标记哈希，不泄露标记明文。

- `products/object_scan`：bundle是gzip-tar的base64，解包后为本地合成Git仓库，含一个历史重写后不可达对象中的secret[...]标记。通过Git对象枚举恢复，返回 {secret:完整标记}。普通文件及正常提交说明必须保持。没有真实密钥/远程服务。
- `products/cleaned_repo`：先确认已恢复标记，再删除仓库中的该标记，包括reflog和不可达对象；保留普通工作区内容与正常提交说明。返回 {bundle:清理后完整仓库tar.gz的base64,files:{普通相对路径:SHA256},messages:[git log --format=%s按新到旧]}。允许任意语义正确仓库重打包，不比tar字节。
- `products/recovery_report`：实际读取清理后的仓库，枚举全部对象验证无secret[...]；返回 {secret:恢复标记,files:普通文件SHA256映射,messages:正常提交说明列表,remaining_secret_objects:0}。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
