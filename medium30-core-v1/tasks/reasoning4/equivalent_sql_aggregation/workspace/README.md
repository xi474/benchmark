# N21 词义统计 SQL 的等价优化

把含重复相关子查询的词义统计 SQL 改写为更少重复工作的查询，保持列名、结果和顺序一致。

## 本版输入与业务范围

性能为核心要求，采用公开可复现的SQLite VM预算，免除不稳定墙钟比值。预算须经参考查询和原始低效查询双向验证。

- `engines/word_statistics`：tables包含words(wordid,word)、senses(wordid,synsetid)、synsets(synsetid,domainid,posid)。按wordid返回统计列表 [{word_id,word,total_synsets,total_senses,distinct_domains,distinct_posids}]，词没有sense也列出0；所有引用合法。
- `engines/top_synsets`：每词按sense行数最多选synset，平局取较小synsetid。返回 [{word_id,top_synsetid,top_synset_sense_count}]，按word_id，只包含至少一个sense的词。
- `engines/optimized_query`：返回通用只读SQLite查询字符串。对所有合法表均应输出8列：word_id,word,total_synsets,total_senses,distinct_domains,distinct_posids,top_synsetid,top_synset_sense_count；只保留total_synsets>=2、distinct_domains>=2、total_senses>=2。按total_senses/total_synsets/distinct_domains降序，再word_id升序，LIMIT 500。不能把当前统计结果硬编码为SQL常量；评测复用该SQL于不同正常数据库。接受任意等价SQL；公开工作量预算为 SQLite VM 步数 <= 200*len(senses)+20000，原始相关子查询作为负例。
- `engines/query_result`：实际在只读SQLite表执行sql，返回 {columns:上述8列名,rows:查询结果二维列表}；不输出或比较SQLite特定格式的执行计划。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
