# N28 定时回复与按唯一收件人采购

收集固定四分钟内的新邮件，到点统一回复，再在三十秒逻辑延迟后按不同发件人数采购并创建提醒。

## 本版输入与业务范围

保留邮件数与唯一发件人数的区别、两阶段逻辑时间和公开指定商品；移除实际等待和真实购买，使用有限模拟动作账本。

- `stages/reply_batch`：emails=[{id,from,at:逻辑秒}]。筛选0<=at<window，按(at,id)排序，统一在window时回复。返回 [{email:ID,to:邮箱,at:window,purpose:'gift_reply'}]。不对自然语言措辞评分。
- `stages/gift_variant`：selection给brand/color/size/product；唯一定位全部字段相等的商品，返回variant ID。输入保证唯一。
- `stages/gift_checkout`：按实际回复的唯一邮箱数量采购，在window+30逻辑秒checkout。date为当前YYYY-MM-DD。返回 {replies,order:{at,variant,quantity},reminder:{date:当月最后一天,all_day:true,title:'Reminder: Hand Out Gifts'}}。同邮箱多邮件都回复但只算一件礼品。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
