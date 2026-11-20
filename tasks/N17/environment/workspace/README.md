# N17 模板配置依赖与最小更新集合（盲编排版）

## 业务范围

保留属性、字典下标和表达式中的 conf 引用；公开一个有限模板表达式语法及合法配置表。最小更新集合是本项目追加的直接消费者。

- `engines/template_dependencies`：templates={模板ID:文本}，只分析 {{ Python兼容表达式 }}；支持 conf 属性、静态字符串下标与算术表达式，不执行模板。提取conf开头访问链，把下标转点号；以options中最长合法前缀作为配置项，忽略notconf及模板普通文本。输入每个conf链至少有一个合法前缀。返回 {模板ID:排序唯一配置键列表}。
- `engines/stylesheet_updates`：changed为合法配置键列表。返回 {dependencies:全部依赖,affected:依赖与changed相交的排序模板ID列表}。
- `engines/reverse_index`：返回 {配置键:排序模板ID列表}。

## 实现与交付契约

完成各组件engine.py和项目入口run_all.py，可添加私有源码辅助模块。各SPEC与contract给出原业务算法、输入文件绑定、输出路径及接口；runtime.py仅提供通用加载、导入和落盘工具。

delivery.json是无序交付清单：component_outputs映射每个组件名与JSON产物路径，result_file指定最终业务结果文件。源码和清单的枚举位置不表示执行顺序。自行组织组件的实现和执行策略。

`python3 run_all.py`须从当前inputs/request.json生成全部组件和额外交付物，并写outputs/final_report.json：{"task":"N17","results":{组件名:对应组件JSON值,...},"result":result_file中的JSON值}。
`python3 check.py`执行你的入口并检查公开例子。正式验收会删除outputs后用新的合法业务输入重建；实现应保存在源码目录。engine.py中的transform、load_payload、build_component仍遵守原SPEC，build_component须能在只提供其绑定输入的干净目录独立工作。

README、SPEC、contract、输入、delivery.json、runtime.py、check.py和公开期望均受保护。run_all.py为可修改入口。评分沿用547单元中的原题注册清单，分别报告公开、核心转换、严格通过和Reward；单题上限2，50%验收完成分加50%严格完整交付奖励。调度策略不另加计分单元，未注册的通用稳健性不计分。
