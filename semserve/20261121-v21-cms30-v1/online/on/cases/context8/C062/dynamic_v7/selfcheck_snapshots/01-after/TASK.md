# C062 多后端快照轮询的关闭屏障

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入`events`按非递减整数time排列，同刻按数组顺序。事件有store与op：open(backend为git/local/s3/azure/oci之一，可给revision，默认0)、poll(job)、complete(job,changed，若changed则含revision)、close。每store只open一次，job唯一，complete与在途job一致；所有开始的job最终均有complete。后端名字不改变生命周期语义。

每store最多一个在途更新。open状态第一次poll启动job，再次poll合并而不替换；closing/closed状态拒绝poll。close无在途job立即返回并关闭；有在途job则发取消，直到对应callback结束才返回。取消后的complete不得发布快照。对closing再次close等待同一屏障；closed再次close立即返回。未取消complete的changed=true发布revision并令updates加1；false保持原快照。

输出events审计：opened、poll_started(job)、poll_coalesced、poll_rejected、cancel_sent(job)、close_waiting、callback_cancelled(job)、snapshot_updated(job)、poll_unchanged(job)、close_returned。字段均含time/store，按照事件处理顺序；一次取消complete先callback_cancelled再close_returned。stores保留backend/state/job/revision/closed_at/updates。close返回后不再改变该store快照。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/store_initializers/work.py` | 对每个 open 事件按其原始位置（十进制字符串）建立初始状态，字段同最终 stores 项。 | `components/store_initializers/result.json` |
| `components/completion_effects/work.py` | 对每个 complete 事件按原始位置记录 [正常完成事件名,新 revision 或 null]。取消与关闭优先级由整合逻辑决定。 | `components/completion_effects/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check store_initializers
python -B component_runtime.py run store_initializers
python -B component_runtime.py check completion_effects
python -B component_runtime.py run completion_effects
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
