# N19 读写路由与事务内可见性

让多个简化仓储通过统一数据库抽象读写；事务内读取必须看到本事务之前的写入，提交后能正常读取。

## 本版输入与业务范围

保留 ReadDB/WriteDB 抽象与事务 builder 的传播，缩为两个仓储和本地 SQLite；首版只验有限顺序事务。

- `stages/album_repository`：返回 definition 独立副本。definition={table:SQLite表名,columns:['id','name']}，所有名称为可信固定标识符。仓储只能通过上游统一数据库连接工作。
- `stages/artist_repository`：同album_repository，提供第二个仓储适配定义。
- `stages/transaction_view`：在本地SQLite执行有限脚本。事件 begin/commit；put={kind:'put',repo:'album'|'artist',id,name}；get={kind:'get',repo,id}。事务中put/get均走事务连接，事务外get走read、put走write；get返回对应name或null。初始数据initial={albums:[{id,name}],artists:[...]}。返回 {reads:[get结果],routes:[每个put/get的'transaction'|'read'|'write'],final:{albums:按id排序行,artists:按id排序行}}。只测顺序事务，无锁竞争/重试。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
