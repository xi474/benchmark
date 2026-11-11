# N17 模板配置依赖与最小更新集合

识别模板中真正使用的 conf 配置项，并根据配置变更找到应重新生成的样式模板。

## 本版输入与业务范围

保留属性、字典下标和表达式中的 conf 引用；公开一个有限模板表达式语法及合法配置表。最小更新集合是本项目追加的直接消费者。

- `engines/template_dependencies`：templates={模板ID:文本}，只分析 {{ Python兼容表达式 }}；支持 conf 属性、静态字符串下标与算术表达式，不执行模板。提取conf开头访问链，把下标转点号；以options中最长合法前缀作为配置项，忽略notconf及模板普通文本。输入每个conf链至少有一个合法前缀。返回 {模板ID:排序唯一配置键列表}。
- `engines/reverse_index`：返回 {配置键:排序模板ID列表}。
- `engines/stylesheet_updates`：changed为合法配置键列表。返回 {dependencies:全部依赖,affected:依赖与changed相交的排序模板ID列表}。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
