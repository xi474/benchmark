# N08 测试日志等级的作用域恢复

为简化日志捕获组件实现等级设置和测试结束恢复，保证后续测试不继承前一个测试的 logger/handler 修改。

## 本版输入与业务范围

保留首次设置前的 logger 和 handler 等级；提供明确 begin/set/end 生命周期，不扩展嵌套并发测试或复杂上下文传播。

- `packages/level_snapshot`：initial={handler:整数阈值,loggers:{名称:整数阈值}}。返回独立拷贝，保存测试开始时等级。
- `packages/captured_records`：events依次为 {kind:'set',logger,level}（同时设置该logger与handler），或 {kind:'emit',logger,level,text}。日志级别>=logger阈值且>=handler阈值才捕获。返回 {state:测试末等级,captured:[捕获的text]}；不修改输入。
- `packages/restored_report`：结束时从首次快照恢复全部等级，再处理下一测试的 emit 事件。返回 {restored:快照,captured:上个测试捕获文本,next_captured:下一测试可见文本}。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
