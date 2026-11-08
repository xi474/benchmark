# V4 Pro普通模式 reward-v2：当前Medium20修订矩阵

**2026-11-09更新：MP04、MP08、MP09、MP10、MP11、MP24因规格不一致/要求未明确，从八套Harness的正式统计中统一排除。当前为原14＋mixed16-v4的16＋Medium20，共50题/臂、400个选定题位。** 新增模型请求0，不改原题、verifier或既有分数。原26题/448题位只作历史审计留档，不再作为当前正式汇总。

[查看修订报告、排除原因及全部指标](medium20-revision-2026-11-09/README.md) · [机器入口](CURRENT.json) · [Medium20逐任务×Harness API矩阵](medium20-revision-2026-11-09/api-task-matrix-medium20-eight-arms.csv)

## 当前正式范围与文件

八臂为Nanobot、OpenCode、Codex、DSH、LangGraph、LATTE planning-adapted、ROMA-local-C0、AOrchestra local-adapted。SDK、LATTE纯native和LATTE-frozen不混入。LATTE四个mixed16独立补跑仍单列，不替换baseline。400是保留题位数，不是正常完成数或成功数。

- [Medium20八臂汇总](medium20-revision-2026-11-09/medium20-summary-8.csv)：reward、API微/宏平均、E2E及各阶段时间、tokens、缓存、费用、资源与自检关联指标。
- [Medium20的160题位全指标](medium20-revision-2026-11-09/medium20-cells-160.csv)。
- [完整400题位CSV](medium20-revision-2026-11-09/cells-400.csv) / [JSON及来源字段](medium20-revision-2026-11-09/results.json)。
- [24组Harness×数据集汇总](medium20-revision-2026-11-09/harness-dataset-summary-24.csv) / [JSON](medium20-revision-2026-11-09/harness-dataset-summary-24.json)，数据集为original14、mixed16-v4、medium20。
- [八臂各50题汇总](medium20-revision-2026-11-09/harness-summary-8.csv)。
- [Medium20 API数值矩阵](medium20-revision-2026-11-09/api-task-matrix-medium20-eight-arms.csv) / [覆盖与分类矩阵](medium20-revision-2026-11-09/api-coverage-medium20-eight-arms.csv)。
- [Medium20输入缓存率矩阵](medium20-revision-2026-11-09/input-cache-matrix-medium20-eight-arms.csv) / [覆盖矩阵](medium20-revision-2026-11-09/cache-coverage-medium20-eight-arms.csv)。原14及mixed16逐题数值未变，当前完整长表保留相同数值。
- [已排除48题位](medium20-revision-2026-11-09/excluded-cells-48.csv) / [仍实际发生的开销](medium20-revision-2026-11-09/excluded-summary-8.csv) / [排除策略](medium20-revision-2026-11-09/exclusion-policy.json)。原题号不重排，原attempt不删除、不改分。
- [已过滤自检窗口](medium20-revision-2026-11-09/self-check-loops.csv) / [七臂350题位并行触发明细](medium20-revision-2026-11-09/parallel-trigger-cells-350.csv)。AOrchestra原生指标在完整JSON的native_metrics字段中，未与其他观测层强行合并。

## 口径边界

规格排除属于事后质量修订，所有臂使用同一名单；不解释为Harness性能提升，保留20题也未自动完成难度重新标定。API微平均按可比题api/通过检查数加总除以分母加总，宏平均按逐题比例平均。原14题无api/分母，focused检查另列。reward归一化不是满分率；invalid_submission/无评分题的API准确率保持null，实际开销仍计入保留集合。

费用是已知结算tokens按历史统一峰价的估算，非账单。剔除规格问题题目不会撤销历史消费；保留集合与排除集合的开销分别报告。ROMA original/release_compatibility_program仍有1个真实未知请求，完整缓存率及完整用量不以0补齐；其他历史未知attempt也仍保留。

跨题5/8并发、ROMA单Harbor/HTTP4和AOrchestra并发/输出限额不同，E2E不构成等资源加速排名。子生命周期、模型/HTTP/工具重叠及递归执行是不同观测层。资源为task-container，远程GPU/显存、内部K/V、能耗和per-agent cgroup未观测；自检关联窗口不代表全部思考/修复增量成本。

## 历史来源与复核

- [原Medium26发布入口归档](README-medium26-archived-2026-11-08.md)：此处及旧命名文件里的26题、56题、448题位均属修订前口径。
- 原七臂392题位、AOrchestra56题、缓存分析等文件保留原字节，作为当前过滤来源。旧机制分析仍为历史范围，不将其56题计数冒充新50题计数。
- [生成器](scripts/build_medium20.py) / [独立校验器](scripts/validate_medium20.py) / [修订文件SHA](medium20-revision-2026-11-09/revision-audit.json) / [完整发布审计](publication-audit.json)。执行`python -B scripts/validate_publication.py`同时验证历史来源与当前400题位，无需API key或模型调用。

只发布脱敏结构化指标、公开题号、hash及报告，不发布原始提示、工具输出、凭据、私有任务或LATTE/ROMA上游源码。正式数据集、reward policy和catalog未修改。不要将本目录或作者验证材料挂载给被测Agent。
