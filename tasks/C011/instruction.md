# C011 ERP、MES、WMS联合滚动生产计划

生成资源、工程状态和物料约束一致的有限滚动生产计划，并以ERP/MES/WMS三种视图交付。所有时间、数量为整数，任务区间[start,end)。freeze之前不能新排产；每个订单必须整单完成或不接，不能拆分、复制。SKU必须在released中，产线qualified含该SKU；时长为routing.setup+routing.per_unit*qty，区间须完整落入该产线一个windows区间，结束≤订单due。

wip是强制保留的已知生产任务，起终点/产线固定，且占据当前产线第一顺位；其他任务start≥本线所有wip结束+changeover。任意同线相邻任务之间至少changeover，含wip。wip的库存已在输入库存外预留，不再消耗lots。

bom递归展开至不作为bom键的叶物料，乘以订单qty；bom无环。对每种叶component，可用物料为substitutes[component]（缺省仅自身）。只有status=PASS且expiry≥该任务end的批次可预留；数量为整数，一个需求可跨批次，全部订单总消耗不能超过各lot.qty。不同component可能竞争同批次，不能独立重复预留。

优化顺序：先最大化优先级1总完成qty，再级2，再级3；再按(priority,due,id)订单顺序，字典序最大化是否完成的0/1向量（优先早到期）；最后按订单id排序的`(id,line,start,end,alloc)`列表字典序最小。alloc为(component,lot,qty)升序，仅列正数量。未排订单不出现在任何业务视图。

输出`{selected:[订单ID升序],erp:{run:{id:run_id,freeze},orders:[...]},mes:[...],wms:[...]}`。ERP orders按wo升序，每项`{wo,run,sku,qty,due,start,end,line,status,parent}`；普通wo=订单ID、status=PLANNED、parent=订单ID；wip的status=WIP_CONT、parent=null。MES按line升序再(start,wo)，每线seq从1连续，项`{run,line,seq,wo,qty,start,end,status}`。WMS按(wo,component,lot,qty)升序，以r0001起编号，项`{reservation,run,wo,component,lot,qty,status:RESERVED}`。run在三视图完全相同。

正常域：订单≤5、线≤3、lot≤7、时间0—12、qty1—2、叶需求单订单每种≤4、优先级1—3、BOM深度≤3；所有引用合法、wip本身可行。此版用确定性JSON业务表替代原三数据库/网关SQL，删除服务部署负担；实际跨数据库写回不在当前接口范围，不能继承I2。共享库存和有限产能联合选择仍须严格验收。

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
| `components/material_demand/work.py` | 按工单 ID 输出递归展开后的基础物料需求映射。 | `components/material_demand/result.json` |
| `components/line_windows/work.py` | 按工单 ID 输出合格产线及可行起止窗口三元组，按产线及起点的原遍历顺序。 | `components/line_windows/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check material_demand
python -B component_runtime.py run material_demand
python -B component_runtime.py check line_windows
python -B component_runtime.py run line_windows
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
