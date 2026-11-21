# N24 COBOL 定长交易文件的 Python 等价迁移（盲编排版）

## 业务范围

保留真实字段宽度及连续有效交易语义；提供源程序与已冻结黄金轨迹，agent 环境只需 Python。GnuCOBOL 仅用于出题方离线生成参考。

- `products/accounts`：按34字符定长记录解析账户，字段 ID4/姓名20/余额10。返回 [{id,name:去掉末尾填充空格,balance:整数}]，保持文件顺序。合法 ASCII 输入。
- `products/settlement`：顺序执行交易。请求中的买卖账户和书均存在，买卖方不同、正常金额且余额足够；当前 owner==seller 才成功。成功时买方余额减金额、卖方增加、owner改买方，向 journal 追加 book4+amount10+seller4+buyer4；不符所有权时三类文件不变。返回 {accounts:重编码定长串,books:重编码定长串,journal:累计交易串,statuses:['accepted'|'rejected',...]}。保持原记录顺序，姓名/书名填充20位，数值填充10位。
- `products/books`：按28字符定长记录解析图书，字段 ID4/书名20/owner4。返回 [{id,title:去掉末尾空格,owner}]，保持文件顺序。
- `products/orders`：逐个解析22字符交易请求：buyer4/seller4/book4/amount10。返回 [{buyer,seller,book,amount:整数}]，保持请求顺序。

## 实现与交付契约

完成各组件engine.py和项目入口run_all.py，可添加私有源码辅助模块。各SPEC与contract给出原业务算法、输入文件绑定、输出路径及接口；runtime.py仅提供通用加载、导入和落盘工具。

delivery.json是无序交付清单：component_outputs映射每个组件名与JSON产物路径，result_file指定最终业务结果文件。源码和清单的枚举位置不表示执行顺序。自行组织组件的实现和执行策略。

`python3 run_all.py`须从当前inputs/request.json生成全部组件和额外交付物，并写outputs/final_report.json：{"task":"N24","results":{组件名:对应组件JSON值,...},"result":result_file中的JSON值}。
`python3 check.py`执行你的入口并检查公开例子。正式验收会删除outputs后用新的合法业务输入重建；实现应保存在源码目录。engine.py中的transform、load_payload、build_component仍遵守原SPEC，build_component须能在只提供其绑定输入的干净目录独立工作。

README、SPEC、contract、输入、delivery.json、runtime.py、check.py和公开期望均受保护。run_all.py为可修改入口。评分沿用547单元中的原题注册清单，分别报告公开、核心转换、严格通过和Reward；单题上限2，50%验收完成分加50%严格完整交付奖励。调度策略不另加计分单元，未注册的通用稳健性不计分。
