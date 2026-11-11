# N15 内部符号链接的保真构建与受限解包

构建保留内部符号链接的归档，并在声明的目标目录内安全解包，核对清单和实际成员。

## 本版输入与业务范围

双源组合：内部链接身份与解包根包含关系。只支持公开的受控虚拟树和tar子集，不要求系统级安全归档工具、未知损坏文件或竞态防御。

- `products/member_plan`：输入为受控虚拟 collection 根目录，nodes=[{path,kind:'file'|'dir'|'symlink',content或target}]，symlink相对所在目录解析。没有循环/悬空链接；外部文件内容由external_files以绝对虚拟路径给出，不读实际工作区外文件。规范化后落在/collection外的成员路径拒绝；内部链接保留为symlink，其相对linkname不展开；外部文件链接复制内容为普通file。返回 {members:按name排序[{name,type,content(仅file),linkname(仅symlink)}],rejected:排序拒绝path}。目录没有多余字段。
- `products/archive`：用tarfile生成真实tar，返回 {tar:base64字节,rejected:计划中的拒绝路径}。成员语义必须与plan一致；允许任何合法tar编码，不按压缩字节逐字匹配。
- `products/archive_report`：实际读取tar成员，不展开符号链接目录。返回 {members:与member_plan同格式且按name排序,rejected:输入rejected}。内部文件/目录链接均保留，不能把目录链接子项复制进去。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
