# C017 多入口线索提交与历史账本核对

输入batches为按顺序处理的批次，每条含email/name/city/source/time，email为合法非空ASCII地址，source非空、time非负整数。email去首尾空格并转小写，name/city压缩连续空白；规范email为身份。name/city可为空，二者均非空时完整。

同一批次必须原子提交：先在临时视图逐条处理；若任一条与已有完整或不完整记录的非空name/city矛盾，整批回滚，包括来源视图、晋升和此前该批新增记录，输出rejected/items=[]。否则每条输出accepted/incomplete/promoted/duplicate。新不完整记录可被后续信息补全并晋升完整记录，保留最早first_contact；非空旧字段不能被空值清掉。已完整记录为不可变审计事实：重复提交不改name/city/first_contact，但来源集合可并入派生来源视图。

最终accepted/incomplete每行含email/name/city/first_contact/sources（sources排序），按email排序；sources为source→所有有效记录email的去重升序列表。返回batches/accepted/incomplete/sources。此题不验真实UI、坏账本恢复或磁盘写失败，只保留多入口身份、晋升、冲突、批原子和派生视图一致性。

实现与交付：在`solution.py`实现`transform(payload)`，返回可JSON序列化的对象；输入不应被修改。`load_payload(path)`读取UTF-8 JSON。`build_component(input_path, output_path)`须读取给定输入、独立计算并写出同一结果，返回该结果；在没有旧产物的目录中也必须工作。三个入口均会单独验收。

`python run_all.py`使用`public_input.json`写入`outputs/result.json`；也支持`--input PATH --output PATH`。`python public_check.py`可运行公开小例。只验公开输入域与核心业务约束，不验任意异常文本或编码风格。

正常规模：最多200个业务事件/记录（另有明确说明的字段按该说明）；标识为非空ASCII字符串、整数有限，事件遵守下列前置条件。除声明的集合排序规则外，事件输出保持处理顺序。

