# 来源与改造说明

此包为26个公开候选方向的本地独立重实现，夹具为新合成数据，未分发官方gold patch、账号、原始GAIA2 parquet或完整上游工程。正式任务不等价于SWE/Pro/Terminal/GAIA2原任务，分数不能直接比较。来源数据版本沿用2026-11-03/04的候选审查快照。

GAIA2来源数据标注CC BY 4.0；本包保留来源ID和链接，并明确静态计划化及语义删减。其余来源保留公开实例归属；未将整个上游项目许可改写为本包许可。

固定来源版本见[来源revision清单](review/source_revisions.json)。

逐题原始难度、测试覆盖、运行环境与改编关系见[原题来源与难度标注](docs/原题来源与难度标注.md)。原标签不自动成为改编后难度。

## 明确的范围修订

- MP02只拼一个变化轴，拒绝重叠坐标；MP03只做fstab/AIX/Linux mount三种固定离线语法。
- MP04采用JSON/CSV/JSONL，JSONL代替原Parquet；普通空值规则写入TASK规格。
- MP06/07/08/09/10/11/12/26输出本地状态/通知/采购计划，不发真实消息或付款；没有多轮反馈。
- MP15限制模块/直属函数和赋值类型注释；MP16限制签名、文档指令和给定MRO。
- MP17公开确定性multipart字节协议；MP18使用四种自包含MANIFEST指令；MP19不执行源码。
- MP20保留schema与引用验证的阶段边界，引用错误原子回退；MP21JSON/内存SQLite替代服务。
- MP22只接受有限MARC XML和给定语言代码；MP23索引也分块，空行/无末尾换行/空文件逐字节恢复。
- MP24修订来源参考查询的跨部门计数：必须某一部门人数>10，EU资格部门可以不同。两个部门各6人不入选。
- MP25直接提供文本，移除OCR；MP26“下周五”明确为下一自然周周五，两端含今天/末日。

## MP01 可关闭成员的硬/软加权投票

- [scikit-learn__scikit-learn-13779](https://github.com/scikit-learn/scikit-learn/pull/13779)

## MP02 单变化轴的数据分片拼接

- [pydata__xarray-3151](https://github.com/pydata/xarray/pull/3151)

## MP03 三种挂载格式的离线事实归并

- [instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf/instruction.md)

## MP04 多格式用户合并与完整冲突报告

- [multi-source-data-merger](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/multi-source-data-merger/instruction.md)

## MP05 跨应用候选并集与相处时长排名

- [scenario_universe_23_8pzn4g](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=34)

## MP06 取消日程后多渠道通知

- [scenario_universe_24_lr8en2](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=64)

## MP07 附件发送后归档与独立清理

- [scenario_universe_21_2m6akl](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=69)

## MP08 节日照片迁移后发送与缺失报告

- [scenario_universe_28_wy635e](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=110)

## MP09 两场座谈会、群邀请与物资采购

- [scenario_universe_29_8hgfug](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=65)

## MP10 晚宴计划、联系人定位与餐具采购

- [scenario_universe_26_135a24](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=66)

## MP11 取消会面、研讨会叫车与图书采购

- [scenario_universe_23_2gyolt](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=73)

## MP12 下载目录归档、邮件清理与目标回复

- [scenario_universe_28_nfnpyk](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=76)

## MP13 聚合特征的行键保真与特征合并

- [scikit-learn__scikit-learn-25747](https://github.com/scikit-learn/scikit-learn/pull/25747)

## MP14 异常链的可移植序列化与报告

- [pytest-dev__pytest-5787](https://github.com/pytest-dev/pytest/pull/5787)

## MP15 普通引用、注解和类型注释的导入分析

- [pylint-dev__pylint-4604](https://github.com/pylint-dev/pylint/pull/4604)

## MP16 API 文档的签名、参数与继承信息聚合

- [sphinx-doc__sphinx-7748](https://github.com/sphinx-doc/sphinx/pull/7748)
- [sphinx-doc__sphinx-9230](https://github.com/sphinx-doc/sphinx/pull/9230)
- [sphinx-doc__sphinx-8548](https://github.com/sphinx-doc/sphinx/pull/8548)

## MP17 文本、内联内容和文件的 multipart 组装

- [instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86/instruction.md)

## MP18 集合文件清单的指令选择与归档元数据

- [instance_ansible__ansible-d2f80991180337e2be23d6883064a67dcbaeb662-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-d2f80991180337e2be23d6883064a67dcbaeb662-vba6da65a0f3baefda7a058ebbd0a8dcafb8512f5/instruction.md)

## MP19 Python 支持模块发现与可重复 ZIP 载荷

- [instance_ansible__ansible-c616e54a6e23fa5616a1d56d243f69576164ef9b-v1055803c3a812189a1133297f7f5468579283f86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_ansible__ansible-c616e54a6e23fa5616a1d56d243f69576164ef9b-v1055803c3a812189a1133297f7f5468579283f86/instruction.md)

## MP20 特性配置的模式、附件与引用一致性

- [instance_flipt-io__flipt-c8d71ad7ea98d97546f01cce4ccb451dbcf37d3b](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_flipt-io__flipt-c8d71ad7ea98d97546f01cce4ccb451dbcf37d3b/instruction.md)
- [instance_flipt-io__flipt-e91615cf07966da41756017a7d571f9fc0fdbe80](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_flipt-io__flipt-e91615cf07966da41756017a7d571f9fc0fdbe80/instruction.md)

## MP21 播放列表重写、条件查询与 M3U 导出

- [instance_navidrome__navidrome-d21932bd1b2379b0ebca2d19e5d8bae91040268a](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_navidrome__navidrome-d21932bd1b2379b0ebca2d19e5d8bae91040268a/instruction.md)
- [instance_navidrome__navidrome-28389fb05e1523564dfc61fa43ed8eb8a10f938c](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_navidrome__navidrome-28389fb05e1523564dfc61fa43ed8eb8a10f938c/instruction.md)

## MP22 MARC 作者标题、语言和主题导入

- [instance_internetarchive__openlibrary-111347e9583372e8ef91c82e0612ea437ae3a9c9-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-111347e9583372e8ef91c82e0612ea437ae3a9c9-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59/instruction.md)
- [instance_internetarchive__openlibrary-3c48b4bb782189e0858e6c3fc7956046cf3e1cfb-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-3c48b4bb782189e0858e6c3fc7956046cf3e1cfb-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59/instruction.md)
- [instance_internetarchive__openlibrary-7c8dc180281491ccaa1b4b43518506323750d1e4-v298a7a812ceed28c4c18355a091f1b268fe56d86](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/tasks/instance_internetarchive__openlibrary-7c8dc180281491ccaa1b4b43518506323750d1e4-v298a7a812ceed28c4c18355a091f1b268fe56d86/instruction.md)

## MP23 受目录容量限制的可逆文件重分片

- [reshard-c4-data](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/reshard-c4-data/instruction.md)

## MP24 大学任职、在读人数与国家集合查询

- [sparql-university](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/sparql-university/instruction.md)

## MP25 文本票据分类、金额提取与归档汇总

- [financial-document-processor](https://github.com/harbor-framework/terminal-bench-2/blob/2fd12b88aafdd04a52c298e3940bcb189f9766d6/financial-document-processor/instruction.md)

## MP26 每日晚餐提醒的去重、冲突取消与通知

- [scenario_universe_25_642cr1](https://huggingface.co/datasets/meta-agents-research-environments/gaia2/viewer/mini/validation?row=86)
