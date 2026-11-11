# N23 损坏 WAL 的修复与数据合并

修复受控变换过的 SQLite WAL，使数据库可读取，并导出包含更新与新增记录的完整 JSON。

## 本版输入与业务范围

对原题含糊的破坏模型做显式补充：给定单字节XOR codec，不做隐藏加密猜测。恢复出的SQLite必须实际含WAL更新和插入。

- `products/base_records`：解码base64的真实SQLite基础库，在临时目录只读查询items(id,name,value)，按id返回记录列表。
- `products/decoded_wal`：公开有限破坏模型：codec.scheme='xor-byte'，每个WAL字节与codec.key(0..255)异或。还原真实WAL，返回base64字节串。不要求猜未知密码或修复任意损坏页。
- `products/recovered`：把真实基础库及还原WAL按同名.db/-wal放到临时目录，让SQLite恢复并查询。返回 {records:按id排序的全部记录,base_count:基础记录数,database:原base64库,wal:还原WAL的base64}。不能仅追加两个记录列表，WAL含旧行更新。组件封装写 outputs/recovery_snapshot.json，业务列表单独写 outputs/recovered.json，不得互相覆盖。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
