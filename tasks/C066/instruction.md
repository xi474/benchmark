# 逻辑复制的事务重放与主键交换

initial 是 {主键: {body,rank}}，其中 body 为字符串或 null，rank 为整数或 null。txs 按到达顺序排列，每项 {lsn,statements}。LSN 为正整数。若 lsn 已成功提交过，返回 REPLAY 并跳过，失败的 LSN 可在以后重试。每个 statement 是一组基于该语句开始时快照的同行变更，old 标识不重复。每项 op 为 I/U/D，U 和 D 要求存在 old。I/U 给出 cols（{name,type,value} 数组）。列 key、body、rank 的类型分别为 text、text、int。非空的 rank 值以十进制整数字符串传入。I 必须提供 key、body、rank 三列。key 始终为非空字符串，body 可为字符串或 null，rank 可为整数字符串或 null。U 缺列继承旧值，body/rank 的显式 null 必须保留。D 无 cols。输入字段名不重复。
一条语句同时移除所有 U/D 的旧身份，再放置 I/U 的新行，所以允许主键置换。不存在的 old、类型标记不符或新键碰撞都会使整个事务 ABORT 并回滚先前语句。每个事务返回 [lsn,"COMMIT"/"ABORT"/"REPLAY"]。最终返回 {log,rows}。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。
