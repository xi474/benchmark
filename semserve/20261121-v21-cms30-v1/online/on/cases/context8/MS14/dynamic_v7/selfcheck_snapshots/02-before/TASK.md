# 共享故障域的可用性报告与持续恢复方案

每个服务由底层运行域和带阈值的中间服务组成。生成可重放的事故报告，并给出在整个值班窗口内能使所有目标恢复正常的最小修复组合。

`domains` 中各域初始为 up。`log` 各行为 [域,生效时刻,收录时刻,状态]。查询给出 `as_of,start,end,targets`。只取收录时刻不大于 as_of 的记录。在每个整数时隙 t 取生效时刻不大于 t 的最新值，同一生效时刻取最后收录的版本。每个域的两时刻组合唯一。down 和 degraded 都算不可用，up 可用。区间为 [start,end)。

`services` 是无环定义，每项 `id,need,inputs` 表示至少 need 个不同的直接输入可用时正常。输入可以是底层域或其他服务。列表顺序任意；同一域可从不同直接输入多次影响服务。目标可以是任一服务或域。

输出按查询顺序排列的列表。每项含 `incidents`、`repairs`。incidents 按目标 ID、再按起点升序，行是 [目标,开始,结束]，结束为首次恢复或窗口尾；每个目标的相邻异常时隙合为一个半开区间。repairs 为所有**包含极小**的永久修复域集合。选中的域在窗口内每个时隙均被强制置为 up；窗口内所有目标必须一直可用。若严格子集也能做到，就不能列出该方案。集合内部按域名升序，各集合先按大小再按成员序列字典序排列。无需修复时应为 [ [] ]。

每次查询独立，窗口至多 30 个时隙。最多 40 个底层域，每个服务至多 40 个输入；记录和修复输出的规模保持稀疏。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/observed_outages/work.py` | 为每个查询逐时隙列出当时可见且实际为 down 的域名数组，升序；按有效时刻再按看到时刻选择最新记录。 | `components/observed_outages/result.json` |
| `components/service_quorums/work.py` | 按服务 ID 索引门槛及直接输入，值为 [need,inputs]；保留输入顺序和共享故障域。 | `components/service_quorums/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check observed_outages
python -B component_runtime.py run observed_outages
python -B component_runtime.py check service_quorums
python -B component_runtime.py run service_quorums
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
