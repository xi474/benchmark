# N10 有限置换群的同态验证

根据有限群的生成元及其目标像，检验它们是否定义一致的同态，并给出所有群元素的映射。

## 本版输入与业务范围

限置换作用于至多 5 个元素、群阶至多 120；使用闭包遍历和置换数组，不安装 SymPy，也不扩展一般无限群。

- `engines/source_group`：generators 是同长度置换数组列表，置换表示 i→perm[i]。复合 a*b 定义为 a[b[i]]。从单位元闭包遍历，返回按置换字典序排序的全部元素列表。作用域≤5，群阶≤120。
- `engines/target_group`：对目标生成元像使用相同置换复合规则计算目标子群并排序。
- `engines/homomorphism`：检查 generators[i]→images[i] 是否定义同态。返回 {valid:false,mapping:[]} 或 {valid:true,mapping:[{source:源置换,target:目标置换},...]}，mapping按源置换字典序。不同生成词到同一源元素必须得到同一像，包含逆元形成的关系。不是单独检查每个像为合法置换。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
