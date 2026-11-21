# 文献综述主题分配与证据图更新

空主题表对应空综述及原图边的去重排序。

topics 是主题的固定顺序。papers 每项包含 id、methods（该论文有实质内容的章节名列表）和 claims（[主题,支撑章节,整数质量] 列表）。仅支撑章节列于本论文 methods 的候选可用；同题同论文保留最大质量。每主题必须选一篇，不得重用论文。依次最大化所有主题中的最低质量、总质量，再取论文ID序列字典序最小解。graph 为现有 [起点,关系,终点] 边，返回 {"review":[[主题,论文ID,质量],...],"graph":[...]}。后者是既有边与每条 [论文ID,"supports",主题] 的去重并集，按三项字典序排序。无完整分配返回 null。字符串比较按大小写原样，最多8主题12论文。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/evidence_scores/work.py` | 按主题输入顺序生成评分表；每行把具有效章节证据的论文 ID 映射到该主题最高质量分。 | `components/evidence_scores/result.json` |
| `components/graph_facts/work.py` | 返回去重并按三元组字典序排列的已有图事实。 | `components/graph_facts/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check evidence_scores
python -B component_runtime.py run evidence_scores
python -B component_runtime.py check graph_facts
python -B component_runtime.py run graph_facts
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
