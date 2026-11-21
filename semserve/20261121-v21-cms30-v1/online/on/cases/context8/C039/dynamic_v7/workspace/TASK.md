# C039 带结构先验的因果图学习与干预

从线性高斯数据的充分统计量选择受先验约束的因果DAG，并计算干预后的均值。输入节点有序列表、协方差正定矩阵covariance、均值mean、sample_size、允许有向边allowed、无父节点root、精确edge_count和max_parents。只能选allowed中的边，root无入边，各节点入度不超过max_parents，整图无有向环，边数精确满足。

对每节点，以父节点作线性最小二乘回归，残差方差为`Cyy-CyP*CPP^-1*CPy`，无父时为Cyy。总分为各节点`sample_size*ln(残差方差)+父数*ln(sample_size)`之和，求最低。比较时分数先四舍五入到9位小数；平局按排序后的(parent,child)边列表字典序。回归斜率和干预使用未舍入值。

intervention把指定节点常量设为value并切断其全部入边。其他节点保留斜率与观测均值确定的截距；输出精确期望均值，不做随机抽样。输出`{feasible:true,edges:[[parent,child]...],score:6位小数,coefficients:[[parent,child,斜率]...],intervened_edges:[...],mean:[按nodes顺序]}`，边和系数按(parent,child)字典序，数值四舍五入6位。无合法DAG返回`{feasible:false}`。

正常域：3—5节点、allowed≤14边、edge_count≤5、max_parents≤3、sample_size≥20。协方差保证对称正定且回归残差大于0.01；候选最佳分数不会处在9位舍入边界，最终数值验收容差1e-5。本改编用充分统计量和期望替代源题CSV与10k随机样本，保留全局DAG先验、参数估计及do干预语义。

## 交付接口

使用Python 3.11及标准库。实现`solution.py`中的：

- `transform(payload)`：接收下述JSON对象并返回规定的JSON值，不修改输入。
- `load_payload(path)`：从任意给定UTF-8 JSON路径读取并返回输入对象。
- `build_component(input_path, output_path)`：读取输入、调用实现，将完整结果写入给定JSON路径并返回该结果。父目录不存在时应建立；不能依赖之前产物或当前工作目录。

运行`python run_all.py --input public_input.json --output outputs/result.json`生成产物；`python run_all.py --check`执行公开示例检查。验收同时直接调用以上三个入口，并在干净目录检查交付物独立运行。只使用题内正常输入域，不考察NaN、任意畸形JSON或错误文本。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/admissible_edges/work.py` | 排除指向根的边，按 allowed 顺序返回节点下标对。 | `components/admissible_edges/result.json` |
| `components/local_regressions/work.py` | 为每个节点及其容许的父集合计算未舍入回归系数；返回每节点一张表，以逗号分隔的升序父下标为键，空集用空字符串。 | `components/local_regressions/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check admissible_edges
python -B component_runtime.py run admissible_edges
python -B component_runtime.py check local_regressions
python -B component_runtime.py run local_regressions
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
