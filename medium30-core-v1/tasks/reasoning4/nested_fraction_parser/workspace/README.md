# N07 嵌套分数表达式的解析与保真输出

解析有限 LaTeX 分数语法，构造正确表达式树，并输出保持除法结合关系的表示与数值结果。

## 本版输入与业务范围

只保留变量、有理数、加乘幂和 frac 的公开子集；用 Fraction 与小型 AST 代替完整 SymPy/ANTLR。

- `engines/expression_ast`：解析公开语法：整数、单字母变量、花括号/圆括号分组、+、*、^和\frac{expr}{expr}。+/*左结合，^只跟非负整数字面量；\frac保留完整分子分母。返回AST：['int',n]、['var',name]、['add'|'mul'|'div'|'pow',left,right]。无隐式乘法、所有输入合法，深度≤8。
- `engines/exact_value`：使用有理数解释AST，values给每个变量整数值且所有分母非零。返回 {numerator:最简有符号整数,denominator:正整数}。
- `engines/expression_report`：返回 {ast:输入AST,value:输入有理数值,text:全括号中缀表示}。int/var直接打印，add/mul/div/pow分别打印 (left+right)/(left*right)/(left/right)/(left^right)，此处斜线表示规则分隔而非输出串；每个二元节点恰有一对外括号。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
