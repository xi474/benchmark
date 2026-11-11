# N30 移动后附件的跨渠道收件人分流

移动指定文件后，把同一新路径附件发给按条件定位的联系人，并把可用消息渠道不同的历史教师分成群聊和邮件两组。

## 本版输入与业务范围

保留文件移动后路径、多个独立联系人条件、渠道分区及群发；内容仅为不透明小文件，不读取或编辑 xlsx。

- `products/moved_document`：Files应用的虚拟快照files={相对路径:不透明文件字节的base64}，夹具为可打开的有效xlsx。移动source到destination，目标父目录可创建。返回 {files:移动后快照,attachment:{path:destination,content:原base64,sha256:解码后实际文件字节摘要}}。source存在、destination未占用。只保留字节，不解析xlsx内部。
- `products/recipients`：people=[{id,teacher:是否现任或曾任历史教师,former,country,pilot:是否曾任飞行员,messages:是否支持Messages}]。目标邮件收件人为email_sender与唯一country=RU且pilot=true联系人之并集。教师排除self后按messages分区。返回 {target_email:排序ID,messages:排序教师ID,fallback_email:排序教师ID}；former不排除教师。
- `products/delivery`：返回 {files:移动后快照,target_email:{to:目标ID,path,sha256},messages:null或{members:教师ID,path,sha256},fallback_email:null或{to:不可达教师ID,path,sha256},attachment_content:原base64内容}。空分区不创建空群/邮件，所有发送引用移动后文件。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
