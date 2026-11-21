# 带依赖批次的单次委派与重试回放

输入 tasks 是无序、无环的任务图，各项含 id、needs、pool、stream、attempts。pools[pool] 是循环选择的虚拟主机列表。feeds[主机][stream] 是循环产生批次的列表，每一批是整数数组；各 (主机,stream) 独立计数，非空列表。initial 为每台主机的初始整数事实值。所有池和流从索引0开始。每轮同时放行轮初全部已满足依赖的任务；同一轮对有状态选择器的消费，以任务 id 字典序为标准。每个任务在整个执行期只消费一次委派选择器和该主机上的一次批次选择器。attempts 为成功所需尝试次数；重试使用已选主机、批次及快照，之前尝试无提交。

每个任务读取轮初该主机事实值 base 和直接父任务的已提交 delta 之和 parent。批内每个 item 的业务结果为 (base+item)×(1+parent)；delta 为批结果之和。该轮所有成功提交结束后，各主机事实值一次性增加委派到其上的 delta 总和。输出 {"tasks":按id键控的 {host,items,base,parent,delta,attempts},"facts":最终主机值,"pool_reads":每个给出的池读取次数,"feed_reads":与 feeds 同形的主机→流→读取次数}。多个同轮任务可能分往同主机。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/dependency_waves/work.py` | 返回各依赖批次，每批含按 ID 升序排列的任务 ID。同批共享同一事实快照。 | `components/dependency_waves/result.json` |
| `components/feed_statistics/work.py` | 每个 host/stream 返回各次循环读取的 [items,数量,总和] 列表，保持原顺序。 | `components/feed_statistics/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check dependency_waves
python -B component_runtime.py run dependency_waves
python -B component_runtime.py check feed_statistics
python -B component_runtime.py run feed_statistics
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
