# N22 Git 遗失对象恢复与彻底清理（盲编排版）

## 业务范围

输入以归档承载真实本地Git仓库。恢复与清理必须在可独立解包的仓库上成立；公开检查只公开标记哈希，不泄露标记明文。

- `products/cleaned_repo`：先确认已恢复标记，再删除仓库中的该标记，包括reflog和不可达对象；保留普通工作区内容与正常提交说明。返回 {bundle:清理后完整仓库tar.gz的base64,files:{普通相对路径:SHA256},messages:[git log --format=%s按新到旧]}。允许任意语义正确仓库重打包，不比tar字节。
- `products/object_scan`：bundle是gzip-tar的base64，解包后为本地合成Git仓库，含一个历史重写后不可达对象中的secret[...]标记。通过Git对象枚举恢复，返回 {secret:完整标记}。普通文件及正常提交说明必须保持。没有真实密钥/远程服务。
- `products/recovery_report`：实际读取清理后的仓库，枚举全部对象验证无secret[...]；返回 {secret:恢复标记,files:普通文件SHA256映射,messages:正常提交说明列表,remaining_secret_objects:0}。

## 实现与交付契约

完成各组件engine.py和项目入口run_all.py，可添加私有源码辅助模块。各SPEC与contract给出原业务算法、输入文件绑定、输出路径及接口；runtime.py仅提供通用加载、导入和落盘工具。

delivery.json是无序交付清单：component_outputs映射每个组件名与JSON产物路径，result_file指定最终业务结果文件。源码和清单的枚举位置不表示执行顺序。自行组织组件的实现和执行策略。

`python3 run_all.py`须从当前inputs/request.json生成全部组件和额外交付物，并写outputs/final_report.json：{"task":"N22","results":{组件名:对应组件JSON值,...},"result":result_file中的JSON值}。
`python3 check.py`执行你的入口并检查公开例子。正式验收会删除outputs后用新的合法业务输入重建；实现应保存在源码目录。engine.py中的transform、load_payload、build_component仍遵守原SPEC，build_component须能在只提供其绑定输入的干净目录独立工作。

README、SPEC、contract、输入、delivery.json、runtime.py、check.py和公开期望均受保护。run_all.py为可修改入口。评分沿用547单元中的原题注册清单，分别报告公开、核心转换、严格通过和Reward；单题上限2，50%验收完成分加50%严格完整交付奖励。调度策略不另加计分单元，未注册的通用稳健性不计分。
