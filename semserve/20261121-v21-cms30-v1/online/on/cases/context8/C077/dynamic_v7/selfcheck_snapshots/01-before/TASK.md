# C077 重叠邮箱修改与延迟刷新

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

events按非递减毫秒time排列，同刻按数组顺序：start(id)、finish(id)、refresh、response(id,failed/stale/items)、advance。修改id唯一且finish对应活跃修改。每次真实fetch依次编号fetch-1等，response对应当前网络请求；failed、stale=1、成功三者互斥，成功含items。计时器在同刻外部事件之前触发。

任何修改在途时不发fetch。refresh或任一修改finish产生待刷新义务；有多个重叠修改时只在最后finish的同次处理发一次，无额外macrotask。已有网络请求或重试计时器时义务合并。成功响应提交items，若尚有额外义务，且无修改阻塞，则同次处理再fetch。

failed不提交，设置唯一now+2000计时器；stale=1不提交，设置唯一now+1000计时器，并保持原request标记为in_flight直至到点。额外refresh不得新增计时器。计时器到点清除旧请求标记并立即重试；若此时修改仍在途，保留义务，最后finish同步重试。后一碰撞优先级是本改编明确裁决，避免“禁止在途修改fetch”与“计时器无条件fetch”相冲突。

输出fetches[{id,time}]、commits[{time,items}]、events审计、state。审计包含fetch(id)、modification_started/finished(id)、retry_scheduled(due,reason=failure/stale)、committed(id)，均有time。state含active排序列表、owed、loading、placeholders(等于loading)、in_flight、retry_at、items(初始[])。待请求/重试/待刷新均loading；成功且无义务才结束loading。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/mutation_membership/work.py` | 对 start/finish 事件按输入位置给出处理后仍活动的修改 ID 有序列表。 | `components/mutation_membership/result.json` |
| `components/response_deadlines/work.py` | 按 response 位置记录 [原因,到期时间]；失败优先于陈旧，延迟分别为 2000/1000，正常相应用 null。 | `components/response_deadlines/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check mutation_membership
python -B component_runtime.py run mutation_membership
python -B component_runtime.py check response_deadlines
python -B component_runtime.py run response_deadlines
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
