# N09 多方日历可用区间的最早交集

读取三份小型 ICS 日历，综合每个人的硬可用时间和已有忙碌事件，找到最早可行的一小时会议并输出 ICS。

## 本版输入与业务范围

沿用源题硬可用时间、午休和缓冲。只取最早硬可行会议；源题含糊的软偏好不作为隐藏要求。日历限公开 UTC VEVENT 子集。

- `stages/alice_availability`：读取有效UTC日历子集 BEGIN:VEVENT/DTSTART/DTEND。无循环/全天事件。对 days 各日从 rule.start/end（午夜后分钟）可用时段扣除既有事件和 breaks；weekday_end 可按星期0=周一缩短结束。若 late_buffer 非null且某事件结束分钟>=threshold，将该事件忙碌结束再延长指定分钟。所有区间半开；返回按开始排序的 [startUTC,endUTC]，格式 YYYYMMDDTHHMMSSZ。事件可覆盖一天，窗口保证最终有解。
- `stages/bob_availability`：读取有效UTC日历子集 BEGIN:VEVENT/DTSTART/DTEND。无循环/全天事件。对 days 各日从 rule.start/end（午夜后分钟）可用时段扣除既有事件和 breaks；weekday_end 可按星期0=周一缩短结束。若 late_buffer 非null且某事件结束分钟>=threshold，将该事件忙碌结束再延长指定分钟。所有区间半开；返回按开始排序的 [startUTC,endUTC]，格式 YYYYMMDDTHHMMSSZ。事件可覆盖一天，窗口保证最终有解。
- `stages/carol_availability`：读取有效UTC日历子集 BEGIN:VEVENT/DTSTART/DTEND。无循环/全天事件。对 days 各日从 rule.start/end（午夜后分钟）可用时段扣除既有事件和 breaks；weekday_end 可按星期0=周一缩短结束。若 late_buffer 非null且某事件结束分钟>=threshold，将该事件忙碌结束再延长指定分钟。所有区间半开；返回按开始排序的 [startUTC,endUTC]，格式 YYYYMMDDTHHMMSSZ。事件可覆盖一天，窗口保证最终有解。
- `stages/meeting`：求三个人可用时间的共同交集，选择最早能容纳连续60分钟的分钟起点。返回 {start:UTC字符串,end:UTC字符串,attendees:输入列表,summary:'Team Planning Meeting'}。只以硬可行且最早为目标，软偏好不参与正式评分。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
