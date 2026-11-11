# optimized_query

返回通用只读SQLite查询字符串。对所有合法表均应输出8列：word_id,word,total_synsets,total_senses,distinct_domains,distinct_posids,top_synsetid,top_synset_sense_count；只保留total_synsets>=2、distinct_domains>=2、total_senses>=2。按total_senses/total_synsets/distinct_domains降序，再word_id升序，LIMIT 500。不能把当前统计结果硬编码为SQL常量；评测复用该SQL于不同正常数据库。接受任意等价SQL；公开工作量预算为 SQLite VM 步数 <= 200*len(senses)+20000，原始相关子查询作为负例。

## API 与文件契约

`transform(payload, contract)` 接收 contract.bindings 对应的字段字典，返回本规格定义的 JSON 值，不修改 payload/contract。`load_payload(path)` 读取合法 JSON。`build_component(root, contract)` 从 root 下的绑定文件加载输入，在目标产物尚不存在时独立完成计算、落盘并返回相同结果。具体路径见 contract.json。提供的 I/O 代码可直接保留。

仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。
