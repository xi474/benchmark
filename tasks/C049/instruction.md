# C049 微型网络的AFAB流水训练

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入layers按执行顺序，每层weight为[out,in]二维数组、bias为[out]；相邻维度匹配，最后输出至少2类。除最后层外均tanh，最后层输出logits。microbatches非空，各含inputs二维数组与targets类别索引；批大小可不同。world_size为1或2且不超过层数。

rank r拥有半开层区间[floor(L*r/world), floor(L*(r+1)/world))。每个微批经过所有stage后才处理下个微批；所有微批前向完成后，再按微批逆序、stage逆序反向。跨stage传递真正激活及其梯度，不得把最后微批的激活用于其他微批。目标为每微批内部平均交叉熵，再对微批等权平均；不同批大小不改变这一权重规则。返回该目标对全部权重/偏置的梯度，不进行优化器更新。

输出loss、gradients[{weight,bias}]、partitions[{stage,start,stop}]与events。每个stage前向有{kind:forward,microbatch,stage}；非末stage紧跟send_activation(source,target)；反向有backward，非首stage紧跟send_gradient(source,target)。events是上述公开调度语义的可审计输出；验收以数值与调度结果为准，不假称能从外部证明内部实现。数值采用float64，验收绝对/相对容差1e-8；参考结果小数保留12位仅供展示，不强制输出位数。

本改编使用小型全连接网络隔离调度与梯度核，不要求下载LLaMA或使用GPU/真实多进程。可以使用NumPy进行数组运算；不得调用自动求导或现成训练器来代替反向内核。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/batch_gradients/work.py` | 按实际 stage 保留每个微批激活并反传；返回整题格式的 loss 和各层 gradients，采用微批等权和 float64。 | `components/batch_gradients/result.json` |
| `components/pipeline_schedule/work.py` | 输出 partitions 和 AFAB 的 events；层边界为 floor(n*r/world)，保留正序前向、逆序反向及跨 stage 发送。 | `components/pipeline_schedule/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check batch_gradients
python -B component_runtime.py run batch_gradients
python -B component_runtime.py check pipeline_schedule
python -B component_runtime.py run pipeline_schedule
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
