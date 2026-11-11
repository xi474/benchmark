# N29 群成员响应阈值触发的出行安排

创建群聊，在固定窗口内有三名不同参与者发言时，安排一次车辆、发送群通知并删除晚间冲突日程。

## 本版输入与业务范围

保留三人阈值与五分钟逻辑窗口；结构化联系人和消息事件，单次阈值触发，不加入预约取消、成员撤销或多轮重试。

- `stages/group`：contacts=[{id,name}]，names列出唯一姓名。返回 {id:'group:new',title:'Happy Astrid Day!',members:按ID排序目标联系人ID}。
- `stages/evening_events`：calendar=[{id,start_minute:当晚午夜后分钟}]；返回开始时间>=1200的事件ID，按ID排序。
- `stages/threshold_actions`：仅统计group:new中members发出的0<=at<window消息，每人只计一次，按(at,id)处理。首次达到threshold时触发一次；之后不再追加订车。返回 {group:输入group,trigger_at:逻辑秒或null,ride:null或{at,pickup:'21:30',vehicle:'van',from:'home',to:'Tegnergatan 8'},notice:null或{at,meet:'20:00'},deleted:触发时evening否则[]}。未达到阈值是正常业务分支。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
