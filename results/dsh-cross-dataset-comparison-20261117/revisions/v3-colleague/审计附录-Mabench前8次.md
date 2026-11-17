# 审计附录：Mabench前8次探索（不进入主汇报）

更新于2026-11-17。沿用用户此前要求，主报告中的Mabench原0、2题只纳入最后4次实际S/M对照，每题每条件一次，M各2名工作子。前8次探索的原attempt、分数与费用没有删除，也没有根据高低分重新筛选。本次新增的8次属于Complex与R3，与此处8次探索不是同一批。

| Trial | 原版本 | 条件 | 原成功 | 子数 | 已结算峰价估算USD | 移出理由 |
| --- | --- | --- | --- | --- | --- | --- |
| tau1-R000-multi-r1 | adapter-dialogue-censored-v1 | M | False | 0 | $0.037821344 | 自然对话适配截断，不作正常质量结果 |
| tau1-R000-single-r1 | adapter-dialogue-censored-v1 | S | False | 0 | $0.041384552 | 自然对话适配截断，不作正常质量结果 |
| tau1-R002-single-r1 | adapter-dialogue-censored-v1 | S | False | 0 | $0.043469976 | 自然对话适配截断，不作正常质量结果 |
| tau1-R002-multi-r1 | adapter-dialogue-censored-v1 | M | False | 0 | $0.058539272 | 自然对话适配截断，不作正常质量结果 |
| tau2-R002-single-r2 | reference-prompt-v2 | S | True | 0 | $0.033601568 | 多Agent条件未触发，不用于实际协作净收益对照 |
| tau2-R002-multi-r2 | reference-prompt-v2 | M | True | 0 | $0.045078616 | 多Agent条件未触发，不用于实际协作净收益对照 |
| tau2-R000-multi-r2 | reference-prompt-v2 | M | True | 0 | $0.030371440 | 多Agent条件未触发，不用于实际协作净收益对照 |
| tau2-R000-single-r2 | reference-prompt-v2 | S | False | 0 | $0.049313000 | 多Agent条件未触发，不用于实际协作净收益对照 |

移出8次的账本仍为104发送／104结算／未知0、峰价估算 **$0.339579768**，非账单。没有将这部分运营成本记作消失。

当前完整运营为153个唯一attempt，7743发送／7741结算／历史未知2，已知峰价估算 **$53.875767528**。主报告移出此8次后为145条，7639发送／7637结算／历史未知2，估算 **$53.536187760**。统计集合有重叠，不另累计。

- [完整153条](all-attempts153.csv)、[主报告145条](reporting-cells145.csv)、[移出的8条原数据](excluded-mabench8.csv)。
- 旧版完整报告由作者归档保留，未纳入同事交付ZIP；本包的153条明细和8条排除记录足以复算此处计数/费用，不需要访问作者原环境。

当前主报告的8次新增按事先登记的整对和三条件slot加入，不重跑／挑选本附录内容。历史异常、未知和成本均保留。
