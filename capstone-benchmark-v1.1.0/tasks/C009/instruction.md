# C009 部分可见班次中的不可逆运输调度

对有限班次进行逐截止点的非预知调度。所有时间为整数格；区间为[start,end)。输入车辆vehicles、司机drivers、供应商suppliers、可见事件events和严格递增rounds。每轮只允许使用visible≤cutoff的事件，按(visible,event ID)处理；未来事件不能改变当前选择。request包含一个新job（其ID唯一）；cancel引用已出现的job。

每次commit=true会把该轮全部拟分配永久提交。提交任务保留车辆、司机、供应商和时间，后轮不能优化替换。取消对已提交且start<当前cutoff的任务无效，记录ignored_cancellations；否则任务从未开始承诺中移除并列入cancelled，释放库存。已完成任务仍计入历史工时和消耗库存。

每个待派job最多一次，车辆type相同且capacity≥quantity，司机types包含车辆类型，供应商ID在job.suppliers中。start为整数，至少max(cutoff,release)，end=start+duration≤deadline，start≤供应商close。车辆/司机不能时间重叠。供应商累计分配quantity不超过stock。司机所有历史/新任务工时之和≤max_work；按时间排序，相邻任务空隙≥break时连续工时归零，否则累计，始终≤max_continuous。

单任务profit=`revenue-quantity*供应商unit_cost-车辆cost*duration`。每轮在固定已提交任务之外，最大化新任务总profit，再最大化新任务数，再取新分配按(job,start,vehicle,driver,supplier)排序后的元组列表字典序最小者；允许不接单。各轮独立优化可见当前需求，不因已知未来事件改变目标。

输出`{rounds:[{cutoff,assignments,profit,cancelled,ignored_cancellations}...]}`。assignments为已有提交和本轮新分配，按上述元组排序；每项含job/vehicle/driver/supplier/start/end/quantity/profit。profit为该列表利润和；取消列表去重升序。正常域：车辆/司机/供应商各1—3个，job总数≤5，round≤4，时间0—12，duration1—4，quantity1—4，所有数值整数、ID唯一且引用合法。该版静态事件重放替代原在线feed/CLI文件，不提供解法DAG；非预知性与不可逆承诺是核心验收。

## 交付接口

使用Python 3.11及标准库。实现`solution.py`中的：

- `transform(payload)`：接收下述JSON对象并返回规定的JSON值，不修改输入。
- `load_payload(path)`：从任意给定UTF-8 JSON路径读取并返回输入对象。
- `build_component(input_path, output_path)`：读取输入、调用实现，将完整结果写入给定JSON路径并返回该结果。父目录不存在时应建立；不能依赖之前产物或当前工作目录。

运行`python run_all.py --input public_input.json --output outputs/result.json`生成产物；`python run_all.py --check`执行公开示例检查。验收同时直接调用以上三个入口，并在干净目录检查交付物独立运行。只使用题内正常输入域，不考察NaN、任意畸形JSON或错误文本。
