# C058 多主机任务、失败恢复与待处理通知

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入`hosts`为有序唯一主机列表，`handlers`为处理器声明顺序，`program`有`pre/roles/includes/tasks/post`五个可省略阶段。阶段由任务或块组成。任务字段`id`、可选`only`主机集合、`fail_hosts`、`notify`处理器名列表。块为`{"block":{"tasks":[],"rescue":[],"always":[]}}`，亦可带`only`。

每主机独立解释同一程序：任务只在满足only时运行，失败任务不通知；同一块的正常任务失败后跳过剩余正常任务，执行rescue；非空rescue成功则恢复该块，rescue失败或无rescue则向外传播失败。always无论前面是否失败都执行，always自身失败也传播。未捕获失败后不进入后续阶段。只有成功任务产生通知；同一阶段通知去重，阶段结束时仅为有通知的主机产生一个flush及各handler执行，声明顺序决定handler顺序。即使该阶段未捕获失败，已产生的通知仍需flush。

输出`batches`为线性策略每轮实际推进的主机/任务对列表，不允许noop或空占位。规范顺序：阶段顺序如上；每阶段正常任务按树前序，在每块中tasks早于rescue早于always，flush在本阶段所有程序节点之后。每轮从各主机下一就绪节点中选规范位置最早者，只推进处于该位置的主机，主机保持输入顺序。节点路径的规范比较按树中数组位置逐级比较；同一数组块的正常、rescue、always分支分别为0/1/2。输出每对`host/task/kind/status`，kind为task/flush/handler；flush额外含`handlers`。处理器名均已声明；`final`记录每主机ok/failed。空输入程序返回空batches。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/host_conditions/work.py` | 每个 host 对应一张节点表，按树位置（各级整数以 / 分隔）记录 [可执行,会失败]；包含块节点。 | `components/host_conditions/result.json` |
| `components/handler_bindings/work.py` | 输出 [处理器声明顺序映射,叶节点到通知清单的映射]。叶节点按同一树位置编码；通知名去重并按声明顺序排列，含 rescue、always。 | `components/handler_bindings/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check host_conditions
python -B component_runtime.py run host_conditions
python -B component_runtime.py check handler_bindings
python -B component_runtime.py run handler_bindings
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
