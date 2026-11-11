# N27 租房收藏整理与固定窗口新房源通知

整理符合城市与预算的收藏，并在固定四分钟逻辑窗口内将新出现的合格房源通知指定朋友。

## 本版输入与业务范围

保留初始收藏、新事件及固定窗口；用注入式逻辑时钟和静态事件清单代替真实等待。城市和价格来自结构化字段，不做开放文本理解。

- `stages/initial_saves`：对初始快照收藏做集合更新：删除指定city中不在闭区间[low,high]的已收藏房源，保存初始列表中同城合格房源，其他城市原收藏不变。返回排序最终ID列表。
- `stages/new_listings`：events=[{at:逻辑秒,property:{id,city,price}}]，ID唯一。仅筛选0<=at<window内合格新房源，按(at,id)返回 [{at,id}]。本版新事件只通知，不额外修改初始收藏。
- `stages/rental_report`：返回 {saved:初始收藏整理结果,notifications:[{to:friend,property:ID,at:上架逻辑秒}]}。不得把旧合格房源当新事件通知。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
