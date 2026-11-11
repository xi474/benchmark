# N03 多继承测试标记的 MRO 汇合

从有效多继承图计算类的 C3 顺序，并按顺序收集本类及祖先各自声明的测试标记。

## 本版输入与业务范围

用类声明表代替 pytest 项目；新增明确的 C3 计算子模块，这是本项目的结构扩展，不称为原修复必需工作量。仅接收合法、可线性化的类图。

- `engines/linearization`：classes 是 {类名:{bases:有序直接基类列表,marks:本地标记JSON值列表}}。输入是无环且可 C3 线性化的有效类图，根类 bases=[]。返回 target 的 C3 类名列表，首项是自己。不执行用户类代码。
- `engines/local_marks`：返回每个类自身声明的 marks 的独立副本字典，不能把继承标记混入本地标记。
- `engines/effective_marks`：按 mro 顺序逐类连接本地标记列表，保留同名不同参数的标记和本地列表顺序。返回 {mro,marks}。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
