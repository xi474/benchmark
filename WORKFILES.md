# C/MS 预建工作区的改编要求与验收

本地 harness 在握手时把需要写同一文件的工作安排为串行，且需要提前获知中间文件的写入位置。这里的目标是让两个业务组件能够分别被实现、启动、验证和保存结果，随后完成一次实际读取两份结果的整合。

## 设计依据

参照本版其余 25 道 MP 和 4 道 N 题的工作区。MP17 有独立的 body、encoding、parts 模块，N11 按 block_layout、cubed、squared 划分工作单元。二者都给分工提供可定位的实现位置和局部接口。部分 MP/N 题在运行时才生成文件，本版 C/MS 把分支槽位及默认最终输出一起预建，以适配上述 runtime。

## 修改要求

1. 每题提供两个有业务含义的组件。各组件只接收约定的输入字段，可以在同级组件尚未实现时，独立运行本组件的公开用例。
2. 每个组件有自己的实现、运行入口、局部检查、输入、预期样例及结果文件。两个组件运行时只覆写各自的结果槽位，整合入口独占最终产物。握手阶段可直接读取工作区根目录的 `work_units.json`，其中逐项给出实现、输入、输出和命令。多个实验可使用各自独立的工作区。
3. 中间结果使用 JSON。汇总核对组件身份和所用输入的摘要，读取两份结果并调用整合逻辑。直接调用 transform 和对新路径调用 build_component 时从传入的当前输入重算。公开样例、隐藏输入、独立构建及完整交付使用同一套业务接口。
4. 保留原题的状态顺序和业务依赖。例如 C066 可以分别推导旧主键消耗与列类型解码，事务提交及回滚仍按日志顺序；MS11 可以分别计算学生成绩和消费金额，匹配与关联区间需要消费两者。组件可以独立写入，并不保证两者耗时相当。
5. 评分沿用逐题冻结 verifier、完整性范围、严格通过与 50% 完整交付奖励。局部样例用于调试。两个模块文件和结果槽的存在本身没有分值。原版档位、六个 harness 的历史覆盖及五轮结果保留其版本标识。

## 同事可以直接试的例子

在 MS11 的 environment/workspace 下，分别实现 components/student_scores/work.py 和 components/buyer_totals/work.py，在 integration.py 中实现 combine。以下两条命令可在不同进程同时运行。

```sh
python -B component_runtime.py run student_scores
python -B component_runtime.py run buyer_totals
```

两个结果分别落在各组件目录的 result.json，随后运行 `python -B component_runtime.py join`，最终文件是 outputs/result.json。每个组件都能用 `check 组件名` 单独检查公开样例。Harbor 标准入口仍是 `harbor run --path tasks/MS11 --agent oracle`。

## 验收口径

离线验收检查两路分别执行、完整输入变动后的旧产物拒收、正常汇总、直接 API 和标准 verifier。参考解与起始桩分别跑正式评分。未修改的 29 个题包按原始逐文件哈希复核。历史五轮成绩不能用作新握手下是否发生委派的观测；实际并行需要结合自研 harness 的子任务创建和执行时间段另行判断。


## 逐题接口

| 题号 | 第一组件 | 第二组件 |
|---|---|---|
| [C007](tasks/C007/instruction.md) | `mobile_cable` · 标准化 ('mobile', 'cable') 渠道记录，返回 [原位置,字段对象] 数组。对象字段 id,first,last,dob,ssn,mail,phone,address，日期 ISO，文字小写去非字母数字，电话及证件仅留数字。 | `internet_streaming` · 标准化 ('internet', 'streaming') 渠道记录，返回 [原位置,字段对象] 数组。对象字段 id,first,last,dob,ssn,mail,phone,address，日期 ISO，文字小写去非字母数字，电话及证件仅留数字。 |
| [C008](tasks/C008/instruction.md) | `relationship_windows` · 将链接和合并登记为 [起点,终点,生效时刻,失效时刻]。保留原顺序并补齐缺省区间。 | `record_subjects` · 按记录顺序产生 [表名,行号,时间,[租户,主体]]，为跨表归一化保留租户作用域。 |
| [C009](tasks/C009/instruction.md) | `visible_events` · 返回按可见时刻及事件 ID 排序的业务事件。 | `crew_compatibility` · 返回每辆车可使用的司机 ID 数组，保留司机声明顺序。 |
| [C011](tasks/C011/instruction.md) | `material_demand` · 按工单 ID 输出递归展开后的基础物料需求映射。 | `line_windows` · 按工单 ID 输出合格产线及可行起止窗口三元组，按产线及起点的原遍历顺序。 |
| [C017](tasks/C017/instruction.md) | `contact_keys` · 保留批次和行序，为每条记录生成清理首尾空白并转小写的邮箱。 | `contact_profiles` · 保留批次和行序，返回 name,city,source,time 对象；姓名与城市的空白折叠为单个空格。 |
| [C031](tasks/C031/instruction.md) | `key_sequences` · 每步按 Linux 终端键表编码为连续字节，返回十六进制字符串列表。 | `session_config` · 输出 rc（固定主提示 PROMPT>、续行提示 CONT>、禁用历史、追加 startup）、timeout（缺省 4）、markers（原顺序的 until，可为 null）。 |
| [C033](tasks/C033/instruction.md) | `elf_segments` · 输出 [入口地址, [[地址,字节],…]]，按加载后的地址升序排列，包括 PT_LOAD 零填充。 | `io_buffers` · 返回 [文件名字节数组映射,标准输入字节数组]，未指定文件或 stdin 时为空。 |
| [C039](tasks/C039/instruction.md) | `admissible_edges` · 排除指向根的边，按 allowed 顺序返回节点下标对。 | `local_regressions` · 为每个节点及其容许的父集合计算未舍入回归系数；返回每节点一张表，以逗号分隔的升序父下标为键，空集用空字符串。 |
| [C049](tasks/C049/instruction.md) | `batch_gradients` · 按实际 stage 保留每个微批激活并反传；返回整题格式的 loss 和各层 gradients，采用微批等权和 float64。 | `pipeline_schedule` · 输出 partitions 和 AFAB 的 events；层边界为 floor(n*r/world)，保留正序前向、逆序反向及跨 stage 发送。 |
| [C055](tasks/C055/instruction.md) | `trusted_bindings` · 解析受信任文档的覆盖和文档内锚点。每个有效键输出 [原源序号,声明位置,[值位置,文本,是否密文,来源是否可信]]；位置为 [源名,行,列]。 | `external_bindings` · 解析不受信任文档的覆盖和文档内锚点。每个有效键输出 [原源序号,声明位置,[值位置,文本,是否密文,来源是否可信]]；位置为 [源名,行,列]。 |
| [C056](tasks/C056/instruction.md) | `dependency_waves` · 返回各依赖批次，每批含按 ID 升序排列的任务 ID。同批共享同一事实快照。 | `feed_statistics` · 每个 host/stream 返回各次循环读取的 [items,数量,总和] 列表，保持原顺序。 |
| [C058](tasks/C058/instruction.md) | `host_conditions` · 每个 host 对应一张节点表，按树位置（各级整数以 / 分隔）记录 [可执行,会失败]；包含块节点。 | `handler_bindings` · 输出 [处理器声明顺序映射,叶节点到通知清单的映射]。叶节点按同一树位置编码；通知名去重并按声明顺序排列，含 rescue、always。 |
| [C062](tasks/C062/instruction.md) | `store_initializers` · 对每个 open 事件按其原始位置（十进制字符串）建立初始状态，字段同最终 stores 项。 | `completion_effects` · 对每个 complete 事件按原始位置记录 [正常完成事件名,新 revision 或 null]。取消与关闭优先级由整合逻辑决定。 |
| [C066](tasks/C066/instruction.md) | `row_identities` · 按事务、语句生成被消费旧主键的去重有序数组，I 不消耗旧主键。 | `column_decoding` · 按事务、语句、行变更生成已解码的列映射。D 用空对象；类型错误用 null，使整合端按事务回滚。 |
| [C067](tasks/C067/instruction.md) | `policy_decisions` · 按输入顺序重放策略变更，为每个 request 原位置生成授权布尔值。 | `service_routes` · 按事件位置返回请求当时的 [集群模式,服务是否可用]；合并端负责授权优先和实际计数。 |
| [C068](tasks/C068/instruction.md) | `cleanup_clock` · 按 get 驱动的 16×TTL 规则生成触发清理的 get 位置，以及下一次清理的时间。输出以位置字符串为键的映射。 | `load_proposals` · 为每个 get 的原始位置生成 [若启动时的完成时刻,value,error]；只有命中未复用时才实际启动。 |
| [C069](tasks/C069/instruction.md) | `user_history` · 记录各续期事件发生时的用户快照，重放 update_user 的 roles、traits；以原位置字符串为键。 | `grant_catalog` · 生成授权条目的有效条件和有序角色/资源集合。以原授权 ID 为键，每项含 approved、expiry、roles、resources。 |
| [C074](tasks/C074/instruction.md) | `directory_snapshots` · 按扫描轮次生成映射，从每个完成目录的逻辑路径映射至 [保留文件映射,可见子目录名升序数组]。按轮累计替换节点。 | `scan_precedence` · 每轮返回完成的逻辑路径，按深度先父后子，同深度维持输入顺序。 |
| [C077](tasks/C077/instruction.md) | `mutation_membership` · 对 start/finish 事件按输入位置给出处理后仍活动的修改 ID 有序列表。 | `response_deadlines` · 按 response 位置记录 [原因,到期时间]；失败优先于陈旧，延迟分别为 2000/1000，正常相应用 null。 |
| [C079](tasks/C079/instruction.md) | `block_manifest` · 返回 [kind,index,hex] 列表；若有缩略图则排首，再按块大小顺序切出文件块。 | `retry_faults` · 按块标签返回可发生的损坏尝试号，限制在 0 至 max_retries，升序去重。 |
| [MS02](tasks/MS02/instruction.md) | `evidence_scores` · 按主题输入顺序生成评分表；每行把具有效章节证据的论文 ID 映射到该主题最高质量分。 | `graph_facts` · 返回去重并按三元组字典序排列的已有图事实。 |
| [MS11](tasks/MS11/instruction.md) | `student_scores` · 按学生 ID 输出课程 1、2 非空成绩的百分制整型均值（sum×100 整除数量）。 | `buyer_totals` · 按买家 ID 汇总属于 Cameras 或 Electronics 的行金额，每行只计一次；无购买为零。 |
| [MS12](tasks/MS12/instruction.md) | `scenario_prefixes` · 输出 [信号历史,该完整叶的权重或 null]，去重生成所有非空前缀，按历史字典序排列。 | `menu_eligibility` · 每个到货信号映射至可供菜品 ID，保持 recipes 顺序，检查难度、原料可得性和过敏限制。 |
| [MS14](tasks/MS14/instruction.md) | `observed_outages` · 为每个查询逐时隙列出当时可见且实际为 down 的域名数组，升序；按有效时刻再按看到时刻选择最新记录。 | `service_quorums` · 按服务 ID 索引门槛及直接输入，值为 [need,inputs]；保留输入顺序和共享故障域。 |
| [MS23](tasks/MS23/instruction.md) | `margin_constraints` · 为每个快照输出 [ab 与 ac 各 a 总量是否相容,按 a,c 行优先展开的 ac 配额]。 | `layer_candidates` · 为每个快照按 b 生成候选层数组。每层候选为 [按 a,c 行优先的计数向量,该层的中位数净分]，满足边际、禁止格和 ac 上限；按向量字典序。 |
| [MS28](tasks/MS28/instruction.md) | `deadline_windows` · 为有截止日的作业返回 [需求,合格时段 ID 升序数组]，先按原始时段和七天半开窗口筛选。 | `remaining_slots` · 每个撤回情景返回仍可用的时段映射，时段 ID 对应 [时刻,容量]。 |
| [MS29](tasks/MS29/instruction.md) | `dish_requirements` · 返回合格的三类菜品组合及合并需求，格式 [菜品 ID 数组,原料到数量映射]，按菜品字典序枚举。 | `purchase_baskets` · 输出所有限量采购篮 [总价,总件数,按排序后 offer 的购买数量向量]；按这三项升序排列。 |
| [MS30](tasks/MS30/instruction.md) | `student_tiers` · 使用 16、17 号课程非空成绩的精确分数比，按原门槛输出学生到 P/D/N 层级映射。 | `market_ranking` · 按最新市场日的 30 天窗口、相对绝对涨跌幅和代号打破平局，返回前 top 个房间代号（保持排名）。 |
| [MS41](tasks/MS41/instruction.md) | `ballot_rules` · 输出 [先验映射,方法提前决胜表]。先验为最简分数。每种方法列出从零票起可达的计数状态（键为逗号分隔的答案票数）；值是已经胜出的答案下标或 null。决胜后不扩展。 | `answer_absorption` · 按 method ID、profile 名输出 [各答案吸收概率,各答案加权成本质量]；向量元素均为约分的 [分子,分母]，保留 answers 顺序。 |
| [MS42](tasks/MS42/instruction.md) | `rubric_mappings` · 返回 [所有可行映射位掩码,旧标签到各新标签的掩码映射]；位序按新标签升序的排列枚举。 | `course_evidence` · 为每门课生成 [项目统计,传递可达表]；统计行 [ID,标签,[成绩和分子,分母],非空数] 按 ID 排序，保留零成绩。可达表的值为有序 ID 数组。 |

## 本版验收记录

| 验收项 | 结果 |
|---|---:|
| 隔离运行组件公开检查（同级组件和整合模块不可用） | 60/60 |
| 公开输入双进程写入后，由独立汇总进程生成正确交付物 | 30/30 |
| 换用另一份冻结输入，双进程落盘，再从磁盘汇总 | 30/30 |
| 参考解严格通过及合计 reward | 30/30，80/80 |
| 起始桩严格通过及合计 reward | 0/30，0/80 |
| 其余 MP/N 题包逐文件与原版一致 | 29/29 |

另从 Harbor 正式入口抽验 C049 与 MS11，oracle 分别得到 2/2、3/3。[Harbor 回执](validation/harbor-smoke.json) · [逐题离线回执](validation/offline.json)
