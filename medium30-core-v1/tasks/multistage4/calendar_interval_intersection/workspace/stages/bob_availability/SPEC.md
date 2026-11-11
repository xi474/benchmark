# bob_availability

读取有效UTC日历子集 BEGIN:VEVENT/DTSTART/DTEND。无循环/全天事件。对 days 各日从 rule.start/end（午夜后分钟）可用时段扣除既有事件和 breaks；weekday_end 可按星期0=周一缩短结束。若 late_buffer 非null且某事件结束分钟>=threshold，将该事件忙碌结束再延长指定分钟。所有区间半开；返回按开始排序的 [startUTC,endUTC]，格式 YYYYMMDDTHHMMSSZ。事件可覆盖一天，窗口保证最终有解。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
