# C068 可取消等待者与共享在途TTL缓存

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入ttl为正整数；events的time为非负非递减整数，同刻按数组顺序。get给唯一id、key、非负delay、JSON value与可选error(默认null)；cancel给已get的id；advance只推进时间。首个miss的load在time+delay完成，同键在途get加入同一次load，忽略其自己的loader参数。不同键互不阻塞。cancel仅使尚未返回的等待者得到cancelled，绝不能取消共享load；即使所有等待者取消，完成结果仍入缓存。

在每个外部事件前，先完成到期的load(同刻按load启动顺序)。完成时stamp缓存，expires=完成时刻+ttl；expires<=访问时刻即过期。成功值与error均缓存，error时结果value为null。get访问时若now>=next_cleanup，移除所有过期项，并令next_cleanup=now+16*ttl；其初始值16*ttl。访问特定key还须立即剔除其过期项。没有后台清理。delay=0也在本次get内完成。cancel和已完成load同刻时完成优先。

输出results按get顺序含id/status/value/error/finished_at；status为ok/error/cancelled；取消的error固定为cancelled。loads仅实际启动的load含key/started_at/finished_at。cache按key排序保留value/error/expires（末尾无需额外清理），以及next_cleanup。输入末尾保证所有get已完成或取消。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/cleanup_clock/work.py` | 按 get 驱动的 16×TTL 规则生成触发清理的 get 位置，以及下一次清理的时间。输出以位置字符串为键的映射。 | `components/cleanup_clock/result.json` |
| `components/load_proposals/work.py` | 为每个 get 的原始位置生成 [若启动时的完成时刻,value,error]；只有命中未复用时才实际启动。 | `components/load_proposals/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check cleanup_clock
python -B component_runtime.py run cleanup_clock
python -B component_runtime.py check load_proposals
python -B component_runtime.py run load_proposals
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
