# N05 数据库时区到业务日期的转换

从各数据库的本地时间表示得到业务时区的正确日期，生成等价的后端查询计划和筛选结果。

## 本版输入与业务范围

保留数据库时区→业务时区方向和同区免转换；首版只用固定 UTC 偏移及可见适配器，降低时区数据库和服务安装负担。

- `stages/backend_a`：rows=[{id,local:'YYYY-MM-DDTHH:MM:SS'}]，source/target 为相对 UTC 的整数分钟偏移（±720以内）。返回 [{id,date:'YYYY-MM-DD'}]，须先从数据库本地区时间换到业务时区再取日期。
- `stages/backend_b`：同 backend_a 的日期语义，用独立后端路径处理；同区时不可重复偏移。
- `stages/date_query`：两后端一致时返回 {dates:a,selected_ids:日期等于 date 的行ID}。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
