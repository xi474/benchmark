# 逻辑复制的事务重放与主键交换

initial 是 {主键: {body,rank}}，其中 body 为字符串或 null，rank 为整数或 null。txs 按到达顺序排列，每项 {lsn,statements}。LSN 为正整数。若 lsn 已成功提交过，返回 REPLAY 并跳过，失败的 LSN 可在以后重试。每个 statement 是一组基于该语句开始时快照的同行变更，old 标识不重复。每项 op 为 I/U/D，U 和 D 要求存在 old。I/U 给出 cols（{name,type,value} 数组）。列 key、body、rank 的类型分别为 text、text、int。非空的 rank 值以十进制整数字符串传入。I 必须提供 key、body、rank 三列。key 始终为非空字符串，body 可为字符串或 null，rank 可为整数字符串或 null。U 缺列继承旧值，body/rank 的显式 null 必须保留。D 无 cols。输入字段名不重复。
一条语句同时移除所有 U/D 的旧身份，再放置 I/U 的新行，所以允许主键置换。不存在的 old、类型标记不符或新键碰撞都会使整个事务 ABORT 并回滚先前语句。每个事务返回 [lsn,"COMMIT"/"ABORT"/"REPLAY"]。最终返回 {log,rows}。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/row_identities/work.py` | 按事务、语句生成被消费旧主键的去重有序数组，I 不消耗旧主键。 | `components/row_identities/result.json` |
| `components/column_decoding/work.py` | 按事务、语句、行变更生成已解码的列映射。D 用空对象；类型错误用 null，使整合端按事务回滚。 | `components/column_decoding/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check row_identities
python -B component_runtime.py run row_identities
python -B component_runtime.py check column_decoding
python -B component_runtime.py run column_decoding
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
