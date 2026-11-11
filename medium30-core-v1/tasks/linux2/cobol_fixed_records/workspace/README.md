# N24 COBOL 定长交易文件的 Python 等价迁移

读取定长账户、图书所有权和交易输入，执行书籍转让，产生与给定 COBOL 程序一致的三个数据文件。

## 本版输入与业务范围

保留真实字段宽度及连续有效交易语义；提供源程序与已冻结黄金轨迹，agent 环境只需 Python。GnuCOBOL 仅用于出题方离线生成参考。

- `products/accounts`：按34字符定长记录解析账户，字段 ID4/姓名20/余额10。返回 [{id,name:去掉末尾填充空格,balance:整数}]，保持文件顺序。合法 ASCII 输入。
- `products/books`：按28字符定长记录解析图书，字段 ID4/书名20/owner4。返回 [{id,title:去掉末尾空格,owner}]，保持文件顺序。
- `products/orders`：逐个解析22字符交易请求：buyer4/seller4/book4/amount10。返回 [{buyer,seller,book,amount:整数}]，保持请求顺序。
- `products/settlement`：顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。成功时买方余额减金额、卖方增加、owner改买方，向 journal 追加 book4+amount10+seller4+buyer4；不符所有权时三类文件不变。返回 {accounts:重编码定长串,books:重编码定长串,journal:累计交易串,statuses:['accepted'|'rejected',...]}。保持原记录顺序，姓名/书名填充20位，数值填充10位。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
