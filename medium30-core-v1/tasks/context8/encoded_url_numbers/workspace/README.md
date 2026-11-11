# N18 保持编码的 URL 数字修改

在指定 URL 段中修改最后一个可操作数字，同时保持其他段与百分号编码原样。

## 本版输入与业务范围

移除 Qt，以原始字符串跨度和有限 URL 分段表示实现；保留作用域、默认 path/query、零填充及非负减法这些源题核心语义。

- `packages/url_segments`：解析合法的 scheme://host[:port]/path[?query][#anchor]。本题限定 ASCII host，无 userinfo/IPv6。返回 {scheme,host,port,path,query,anchor}；缺失 port/query/anchor 用 null，保留原始字节和空 query/anchor。path 可为空；不得 unquote。
- `packages/numeric_target`：依 host,port,path,query,anchor 的 URL 顺序，在给定 segments 中找到最后一个可修改连续 ASCII 数字串。合法 %XX 三字符内的数字必须屏蔽；其后的普通数字可修改。返回 {segment,start,end,text}，start/end 是对应原始段的0基半开跨度。输入保证存在可选数字。
- `packages/modified_url`：operation=increment/decrement，count 是非负整数，输入保证结果非负。仅替换目标跨度；原字符串若有前导零，尽可能保持原宽度，超出时扩宽；原值无前导零则不补零。返回完整新 URL 字符串，其余部分逐字保持。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
