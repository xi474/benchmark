# GLM-5.3 low：Medium5中四题 × OpenCode / Codex / DSH 原生trace

本包对应用户提供的《Medium5-GLM53-四题七Harness对照》中的**MP01、MP02、MP03、MP06**，只发布这三个Harness的12个已选定attempt。没有重新调用模型、补跑题目或更改成绩。

## 下载与查看

- [全部12份trace打包下载](traces-all-12.zip)。
- [OpenCode四题](opencode/) · [Codex四题](codex/) · [DSH四题](dsh/)。
- [机器索引与报告指标核对](manifest.json) · [逐题CSV](cases.csv) · [原始与导出文件哈希](SOURCE_INDEX.json) · [导出校验](EXPORT_VALIDATION.json)。

## 按题定位

- **MP01：可关闭成员的硬/软加权投票** — [OpenCode](opencode/MP01/README.md) · [Codex](codex/MP01/README.md) · [DSH](dsh/MP01/README.md)。
- **MP02：单变化轴的数据分片拼接** — [OpenCode](opencode/MP02/README.md) · [Codex](codex/MP02/README.md) · [DSH](dsh/MP02/README.md)。
- **MP03：三种挂载格式的离线事实归并** — [OpenCode](opencode/MP03/README.md) · [Codex](codex/MP03/README.md) · [DSH](dsh/MP03/README.md)。
- **MP06：取消日程后多渠道通知** — [OpenCode](opencode/MP06/README.md) · [Codex](codex/MP06/README.md) · [DSH](dsh/MP06/README.md)。

## 内容和运行版本

- OpenCode使用报告中的**修复版R3**，没有拿旧输出上限批次替换。原生stdout事件和SQLite session/message/part解码导出均保留，含工具参数与结果；SQLite二进制及Git snapshot对象不发布。
- Codex MP01来自原R1，MP02/03/06来自独立恢复批。保留原生rollout、trajectory、实际请求观察、资源、工具和会话监控。
- DSH保留原headless stream和解压后的原生session v4 JSONL，另附资源和原生事件。
- 每个case的gateway-requests只筛选本trial，逐请求快照也只对应这个trial；保留实际模型/low模式、工具/提示观察、usage与结算，未混入其他任务。
- 新版Reward是保存提交的离线重评分；trace来自原实际模型运行。OpenCode MP01/03/06保留EPIPE异常及原监控失败标签，Codex MP01保留非零退出标签，不能把有评分说成全部正常退出。

## 脱敏、完整性与解释边界

已对上传副本清除凭据/认证头，并把本机个人路径转换为local-artifacts定位符。未裁剪实际工具参数、工具结果或终态来制造成功记录；缺失/未观察仍保留。所有source SHA为本地原始字节的摘要，published SHA针对脱敏后的公开文件，两者不必相等。
原生文件、统一telemetry和框架推导DAG分开保留，工具并发不自动等于多Agent；不根据空children字段补造子Agent数量。运行日志若引用本机运行目录或源码哈希，该位置是证据定位符，不是随包提供的执行环境。
本包不附正式隐藏verifier、参考答案、授权配置或原数据库二进制。所有原件仍在本地，只生成公开副本。三组四题的Reward、Strict、转换检查分子/分母、E2E、输入缓存比和费用均与所给报告核对；费用为估算非账单。
12份所选trace请求全部结算unknown0，仅描述此子集，不清零其他历史批次的未知用量。

[原六Harness对比报告](https://github.com/xi474/benchmark/blob/d750fef43e4ccfbcb0d2c25ddd67fb8f9707c5d6/experiments/glm-v4pro-core6-medium5-2026-11-10/README.md) · [五题版本和任务哈希](https://github.com/xi474/benchmark/blob/d750fef43e4ccfbcb0d2c25ddd67fb8f9707c5d6/experiments/glm-v4pro-core6-medium5-2026-11-10/medium5-selection.json)。
