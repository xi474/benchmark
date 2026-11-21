# C007 多渠道客户实体识别
四个渠道的正常记录含同人重复、姓名变体、联系方式拼写差错和共享家庭字段。实现transform，返回{clusters:[[record_id,...],...]}，每条记录恰好出现一次，簇编号/排序不影响质量判定。不提供完整候选边或配对分数，需自己生成匹配候选并聚类。

records的id在全输入唯一；source为mobile/internet/cable/streaming。fields按各源数据字典：mobile(first,last,dob YYYY-MM-DD,ssn,email,phone,address)；internet(full_name为first last,birth_date MM/DD/YYYY,mail,tel,street)；cable(last_first为last,first,birth YYYYMMDD,government_id,contact,phone,location)；streaming(customer为first last,date_of_birth DD Mon YYYY,email,telephone,address)。大小写、电话号码及地址中的标点/空格仅为正常表示差异。邮箱可为空、可由家庭成员共享，也可有一字符替换/插入/删除；相同邮箱不能单独证明同人。日期是有效真实日期。

不同人可能共享电话/地址/姓氏，双胞胎还可共享生日。ambiguous_names给出有歧义的昵称，例如Pat可能是Patrick或Patricia，不能无条件展开合并。非歧义的完整first name是可用的区分证据；9位政府标识在正常域中准确，4位只表示完整政府标识的后4位，其他情况为空；部分标识必须结合家庭/姓名/生日等证据，不能视为全局唯一。cable也可使用ambiguous_names中的昵称。每个需要消歧的记录都有可见完整姓名、强标识或可匹配邮箱证据，不依赖隐藏性别知识；无观察证据能区分的潜在身份不会用于严格扣分。

采用上游pairwise质量：global precision>=0.98、recall>=0.96、F1>=0.97；家庭冲突子集precision>=0.93、recall>=0.90、F1>=0.91。簇转为同人pair后计分。正式验收有已生成的潜在身份用于计算，但接受任何达到这些公开指标的合法聚类；不要求与参考簇列表逐字一致。未预测任何pair时precision=1，实际存在同人pair时recall=0。公开检查使用小型带真值例子，隐藏测例只改变正常实例。

正常规模：四源共最多24000条记录、家庭通常有1—2人，每人2—4条跨源记录。需要可扩展候选召回；不要求全局枚举所有分区或指定算法。无网络、模型训练或外部库安装。

## 交付
实现solution.py的transform(payload)、load_payload(path)、build_component(input_path,output_path)。后者在干净目录读取输入、计算、写入并返回JSON结果；不得依赖旧产物。运行python run_all.py --input PATH --output PATH；python public_check.py执行公开示例。公开契约和检查文件受保护，业务实现可自由重构。只验下述正常业务域，不验任意坏输入、NaN、错误文案或代码风格。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/mobile_cable/work.py` | 标准化 ('mobile', 'cable') 渠道记录，返回 [原位置,字段对象] 数组。对象字段 id,first,last,dob,ssn,mail,phone,address，日期 ISO，文字小写去非字母数字，电话及证件仅留数字。 | `components/mobile_cable/result.json` |
| `components/internet_streaming/work.py` | 标准化 ('internet', 'streaming') 渠道记录，返回 [原位置,字段对象] 数组。对象字段 id,first,last,dob,ssn,mail,phone,address，日期 ISO，文字小写去非字母数字，电话及证件仅留数字。 | `components/internet_streaming/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check mobile_cable
python -B component_runtime.py run mobile_cable
python -B component_runtime.py check internet_streaming
python -B component_runtime.py run internet_streaming
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
