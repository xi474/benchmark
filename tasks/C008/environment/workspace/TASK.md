# C008 跨租户有效期合并的匿名化

输入seed为整数，records每项含table/id/tenant/subject/time，links和merges每项含a:[tenant,subject]、b:[tenant,subject]，可含from(缺省0)、to(缺省10^18)。所有区间为左闭右开，time为非负整数。

在每条记录自己的time，取所有有效links/merges形成的无向等价关系传递闭包。规范主体为连通分量中字典序最小的(tenant,subject)二元组，不能把不同租户的同名ID直接混同。令raw为`json.dumps([str(seed), canonical_tenant, canonical_subject], ensure_ascii=True,separators=(',',':'))`的UTF-8编码；token为`ref_`加SHA256前12个小写十六进制字符。同一有效规范主体跨表使用同token，变化seed须重新计算。

返回`{records:[{table,id,time,token},...]}`，保持记录顺序、行数和公开字段；不输出原主体。最大200记录/关系，最多200种time。本题输入为静态快照；有效日期不代表运行中的业务历史。

实现与交付：在`solution.py`实现`transform(payload)`，返回可JSON序列化的对象；输入不应被修改。`load_payload(path)`读取UTF-8 JSON。`build_component(input_path, output_path)`须读取给定输入、独立计算并写出同一结果，返回该结果；在没有旧产物的目录中也必须工作。三个入口均会单独验收。

`python run_all.py`使用`public_input.json`写入`outputs/result.json`；也支持`--input PATH --output PATH`。`python public_check.py`可运行公开小例。只验公开输入域与核心业务约束，不验任意异常文本或编码风格。

正常规模：最多200个业务事件/记录（另有明确说明的字段按该说明）；标识为非空ASCII字符串、整数有限，事件遵守下列前置条件。除声明的集合排序规则外，事件输出保持处理顺序。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/relationship_windows/work.py` | 将链接和合并登记为 [起点,终点,生效时刻,失效时刻]。保留原顺序并补齐缺省区间。 | `components/relationship_windows/result.json` |
| `components/record_subjects/work.py` | 按记录顺序产生 [表名,行号,时间,[租户,主体]]，为跨表归一化保留租户作用域。 | `components/record_subjects/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check relationship_windows
python -B component_runtime.py run relationship_windows
python -B component_runtime.py check record_subjects
python -B component_runtime.py run record_subjects
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
