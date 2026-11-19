# C007 多渠道客户实体识别
四个渠道的正常记录含同人重复、姓名变体、联系方式拼写差错和共享家庭字段。实现transform，返回{clusters:[[record_id,...],...]}，每条记录恰好出现一次，簇编号/排序不影响质量判定。不提供完整候选边或配对分数，需自己生成匹配候选并聚类。

records的id在全输入唯一；source为mobile/internet/cable/streaming。fields按各源数据字典：mobile(first,last,dob YYYY-MM-DD,ssn,email,phone,address)；internet(full_name为first last,birth_date MM/DD/YYYY,mail,tel,street)；cable(last_first为last,first,birth YYYYMMDD,government_id,contact,phone,location)；streaming(customer为first last,date_of_birth DD Mon YYYY,email,telephone,address)。大小写、电话号码及地址中的标点/空格仅为正常表示差异。邮箱可为空、可由家庭成员共享，也可有一字符替换/插入/删除；相同邮箱不能单独证明同人。日期是有效真实日期。

不同人可能共享电话/地址/姓氏，双胞胎还可共享生日。ambiguous_names给出有歧义的昵称，例如Pat可能是Patrick或Patricia，不能无条件展开合并。非歧义的完整first name是可用的区分证据；9位政府标识在正常域中准确，4位只表示完整政府标识的后4位，其他情况为空；部分标识必须结合家庭/姓名/生日等证据，不能视为全局唯一。cable也可使用ambiguous_names中的昵称。每个需要消歧的记录都有可见完整姓名、强标识或可匹配邮箱证据，不依赖隐藏性别知识；无观察证据能区分的潜在身份不会用于严格扣分。

采用上游pairwise质量：global precision>=0.98、recall>=0.96、F1>=0.97；家庭冲突子集precision>=0.93、recall>=0.90、F1>=0.91。簇转为同人pair后计分。正式验收有已生成的潜在身份用于计算，但接受任何达到这些公开指标的合法聚类；不要求与参考簇列表逐字一致。未预测任何pair时precision=1，实际存在同人pair时recall=0。公开检查使用小型带真值例子，隐藏测例只改变正常实例。

正常规模：四源共最多24000条记录、家庭通常有1—2人，每人2—4条跨源记录。需要可扩展候选召回；不要求全局枚举所有分区或指定算法。无网络、模型训练或外部库安装。

## 交付
实现solution.py的transform(payload)、load_payload(path)、build_component(input_path,output_path)。后者在干净目录读取输入、计算、写入并返回JSON结果；不得依赖旧产物。运行python run_all.py --input PATH --output PATH；python public_check.py执行公开示例。公开契约和检查文件受保护，业务实现可自由重构。只验下述正常业务域，不验任意坏输入、NaN、错误文案或代码风格。
