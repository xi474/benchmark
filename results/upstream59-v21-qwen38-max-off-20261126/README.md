# Qwen3.8-Max 关闭推理 · Upstream59 v2.1.0 六套完整结果与 trace

**59题 × 6 Harness＝354个最终选定题位**。包含所有 **394条 attempt 记录：387次实际模型运行＋7条零发送隔离记录**；33次被替代的旧付费运行及一笔429未知用量均保留。不是只发布成功案例。

[完整中文报告与图表](report/报告.md) · [交互逐题表](report/dashboard.html) · [354格指标CSV](report/selected-cells.csv) · [全部attempt索引](attempt-index.csv) · [机器可读完整目录](trace-manifest.json) · [校验清单](SHA256SUMS)

## 包含什么

每个attempt包包含已保存的原生会话/事件、工具调用、模型观察与完整请求快照、资源采样、Harbor起止/日志、候选代码和产物、正式与离线评分回执，以及该attempt独立的网关事件。批次包另外保留完整账本、所有网关生命周期事件、checkpoint、注册与运行时修复源码。

DSH压缩会话解码为JSONL；OpenCode数据库连同WAL先复制到临时目录，完整导出schema和所有逻辑表为JSONL，源DB/WAL/SHM哈希保留。SQLite页布局不作为逻辑执行证据发布。没有制造源中缺失的事件。

发布副本只脱敏凭据、认证字段及本机绝对路径；普通长载荷、模型生成内容、事件次序、Agent/会话ID、时间、用量与异常保留。原件不修改，每个文件记录源SHA-256与发布SHA-256。Git对象/快照元数据、安装依赖、Python/pytest缓存及符号链接不作为trace复制，逐包case.json列出省略项；凭据env和指针从不上传。

## 指标与异常口径

使用delivery-bonus-50-v1：reward=I×W×(0.5×冻结登记核心通过率＋0.5×严格通过)，每套满分138。API独立统计803个核心转换用例；完整E2E为Harbor整次起止。354格选定结果usage全部结算；历史15630发出/15629结算/1未知。目录价估算不是Token Plan实际扣费。

LATTE适配版：56次五轮空规划、2次100轮未完成、C031一份正常部分分，不能以低耗时推断效率高。其余15次累计2Mtoken闸门、1次原生context超限、11次完整性失败均保留；原6并发与恢复单/双题并发的资源差异见报告。

## 354个选定题位的下载入口

下面是最终选定attempt。各任务的旧attempt可从[完整索引](attempt-index.csv)按harness/task_id/source_batch找到，不会被选定结果覆盖。

|任务|Codex|DSH|OpenCode|LangGraph|LATTE适配版|Nanobot|
|---|---|---|---|---|---|---|
|C007|[trace](traces/codex/C007/original.zip)|[trace](traces/dsh/C007/original.zip)|[trace](traces/opencode/C007/opencode_git_repair.zip)|[trace](traces/langgraph/C007/original.zip)|[trace](traces/latte-planning-adapted/C007/latte_workspace_repair.zip)|[trace](traces/nanobot/C007/original.zip)|
|C008|[trace](traces/codex/C008/original.zip)|[trace](traces/dsh/C008/original.zip)|[trace](traces/opencode/C008/opencode_git_repair.zip)|[trace](traces/langgraph/C008/original.zip)|[trace](traces/latte-planning-adapted/C008/latte_workspace_repair.zip)|[trace](traces/nanobot/C008/original.zip)|
|C009|[trace](traces/codex/C009/original.zip)|[trace](traces/dsh/C009/original.zip)|[trace](traces/opencode/C009/opencode_git_repair.zip)|[trace](traces/langgraph/C009/original.zip)|[trace](traces/latte-planning-adapted/C009/latte_workspace_repair.zip)|[trace](traces/nanobot/C009/original.zip)|
|C011|[trace](traces/codex/C011/original.zip)|[trace](traces/dsh/C011/original.zip)|[trace](traces/opencode/C011/opencode_git_repair.zip)|[trace](traces/langgraph/C011/original.zip)|[trace](traces/latte-planning-adapted/C011/latte_workspace_repair.zip)|[trace](traces/nanobot/C011/original.zip)|
|C017|[trace](traces/codex/C017/original.zip)|[trace](traces/dsh/C017/original.zip)|[trace](traces/opencode/C017/opencode_git_repair.zip)|[trace](traces/langgraph/C017/original.zip)|[trace](traces/latte-planning-adapted/C017/latte_workspace_repair.zip)|[trace](traces/nanobot/C017/original.zip)|
|C031|[trace](traces/codex/C031/original.zip)|[trace](traces/dsh/C031/original.zip)|[trace](traces/opencode/C031/opencode_git_repair.zip)|[trace](traces/langgraph/C031/original.zip)|[trace](traces/latte-planning-adapted/C031/latte_workspace_repair.zip)|[trace](traces/nanobot/C031/original.zip)|
|C033|[trace](traces/codex/C033/original.zip)|[trace](traces/dsh/C033/original.zip)|[trace](traces/opencode/C033/opencode_git_repair.zip)|[trace](traces/langgraph/C033/original.zip)|[trace](traces/latte-planning-adapted/C033/latte_workspace_repair.zip)|[trace](traces/nanobot/C033/original.zip)|
|C039|[trace](traces/codex/C039/original.zip)|[trace](traces/dsh/C039/original.zip)|[trace](traces/opencode/C039/original.zip)|[trace](traces/langgraph/C039/original.zip)|[trace](traces/latte-planning-adapted/C039/latte_workspace_repair.zip)|[trace](traces/nanobot/C039/original.zip)|
|C049|[trace](traces/codex/C049/original.zip)|[trace](traces/dsh/C049/original.zip)|[trace](traces/opencode/C049/original.zip)|[trace](traces/langgraph/C049/original.zip)|[trace](traces/latte-planning-adapted/C049/latte_workspace_repair.zip)|[trace](traces/nanobot/C049/original.zip)|
|C055|[trace](traces/codex/C055/original.zip)|[trace](traces/dsh/C055/original.zip)|[trace](traces/opencode/C055/original.zip)|[trace](traces/langgraph/C055/original.zip)|[trace](traces/latte-planning-adapted/C055/latte_remaining_two_rate_limit_retry.zip)|[trace](traces/nanobot/C055/original.zip)|
|C056|[trace](traces/codex/C056/original.zip)|[trace](traces/dsh/C056/original.zip)|[trace](traces/opencode/C056/original.zip)|[trace](traces/langgraph/C056/original.zip)|[trace](traces/latte-planning-adapted/C056/latte_workspace_repair.zip)|[trace](traces/nanobot/C056/original.zip)|
|C058|[trace](traces/codex/C058/original.zip)|[trace](traces/dsh/C058/original.zip)|[trace](traces/opencode/C058/original.zip)|[trace](traces/langgraph/C058/original.zip)|[trace](traces/latte-planning-adapted/C058/latte_workspace_repair.zip)|[trace](traces/nanobot/C058/original.zip)|
|C062|[trace](traces/codex/C062/original.zip)|[trace](traces/dsh/C062/original.zip)|[trace](traces/opencode/C062/original.zip)|[trace](traces/langgraph/C062/original.zip)|[trace](traces/latte-planning-adapted/C062/latte_workspace_repair.zip)|[trace](traces/nanobot/C062/original.zip)|
|C066|[trace](traces/codex/C066/original.zip)|[trace](traces/dsh/C066/original.zip)|[trace](traces/opencode/C066/original.zip)|[trace](traces/langgraph/C066/original.zip)|[trace](traces/latte-planning-adapted/C066/latte_workspace_repair.zip)|[trace](traces/nanobot/C066/original.zip)|
|C067|[trace](traces/codex/C067/original.zip)|[trace](traces/dsh/C067/original.zip)|[trace](traces/opencode/C067/original.zip)|[trace](traces/langgraph/C067/original.zip)|[trace](traces/latte-planning-adapted/C067/latte_workspace_repair.zip)|[trace](traces/nanobot/C067/original.zip)|
|C068|[trace](traces/codex/C068/original.zip)|[trace](traces/dsh/C068/original.zip)|[trace](traces/opencode/C068/original.zip)|[trace](traces/langgraph/C068/original.zip)|[trace](traces/latte-planning-adapted/C068/latte_workspace_repair.zip)|[trace](traces/nanobot/C068/original.zip)|
|C069|[trace](traces/codex/C069/original.zip)|[trace](traces/dsh/C069/original.zip)|[trace](traces/opencode/C069/original.zip)|[trace](traces/langgraph/C069/original.zip)|[trace](traces/latte-planning-adapted/C069/latte_workspace_repair.zip)|[trace](traces/nanobot/C069/original.zip)|
|C074|[trace](traces/codex/C074/original.zip)|[trace](traces/dsh/C074/original.zip)|[trace](traces/opencode/C074/original.zip)|[trace](traces/langgraph/C074/original.zip)|[trace](traces/latte-planning-adapted/C074/latte_workspace_repair.zip)|[trace](traces/nanobot/C074/original.zip)|
|C077|[trace](traces/codex/C077/original.zip)|[trace](traces/dsh/C077/original.zip)|[trace](traces/opencode/C077/original.zip)|[trace](traces/langgraph/C077/original.zip)|[trace](traces/latte-planning-adapted/C077/latte_workspace_repair.zip)|[trace](traces/nanobot/C077/original.zip)|
|C079|[trace](traces/codex/C079/original.zip)|[trace](traces/dsh/C079/original.zip)|[trace](traces/opencode/C079/original.zip)|[trace](traces/langgraph/C079/original.zip)|[trace](traces/latte-planning-adapted/C079/latte_workspace_repair.zip)|[trace](traces/nanobot/C079/original.zip)|
|MP01|[trace](traces/codex/MP01/original.zip)|[trace](traces/dsh/MP01/original.zip)|[trace](traces/opencode/MP01/original.zip)|[trace](traces/langgraph/MP01/original.zip)|[trace](traces/latte-planning-adapted/MP01/original.zip)|[trace](traces/nanobot/MP01/original.zip)|
|MP02|[trace](traces/codex/MP02/original.zip)|[trace](traces/dsh/MP02/original.zip)|[trace](traces/opencode/MP02/original.zip)|[trace](traces/langgraph/MP02/original.zip)|[trace](traces/latte-planning-adapted/MP02/original.zip)|[trace](traces/nanobot/MP02/original.zip)|
|MP03|[trace](traces/codex/MP03/original.zip)|[trace](traces/dsh/MP03/original.zip)|[trace](traces/opencode/MP03/original.zip)|[trace](traces/langgraph/MP03/original.zip)|[trace](traces/latte-planning-adapted/MP03/original.zip)|[trace](traces/nanobot/MP03/original.zip)|
|MP04|[trace](traces/codex/MP04/original.zip)|[trace](traces/dsh/MP04/original.zip)|[trace](traces/opencode/MP04/original.zip)|[trace](traces/langgraph/MP04/original.zip)|[trace](traces/latte-planning-adapted/MP04/original.zip)|[trace](traces/nanobot/MP04/original.zip)|
|MP05|[trace](traces/codex/MP05/original.zip)|[trace](traces/dsh/MP05/original.zip)|[trace](traces/opencode/MP05/original.zip)|[trace](traces/langgraph/MP05/original.zip)|[trace](traces/latte-planning-adapted/MP05/original.zip)|[trace](traces/nanobot/MP05/original.zip)|
|MP06|[trace](traces/codex/MP06/original.zip)|[trace](traces/dsh/MP06/original.zip)|[trace](traces/opencode/MP06/original.zip)|[trace](traces/langgraph/MP06/original.zip)|[trace](traces/latte-planning-adapted/MP06/original.zip)|[trace](traces/nanobot/MP06/original.zip)|
|MP07|[trace](traces/codex/MP07/original.zip)|[trace](traces/dsh/MP07/original.zip)|[trace](traces/opencode/MP07/original.zip)|[trace](traces/langgraph/MP07/original.zip)|[trace](traces/latte-planning-adapted/MP07/original.zip)|[trace](traces/nanobot/MP07/original.zip)|
|MP08|[trace](traces/codex/MP08/original.zip)|[trace](traces/dsh/MP08/original.zip)|[trace](traces/opencode/MP08/original.zip)|[trace](traces/langgraph/MP08/original.zip)|[trace](traces/latte-planning-adapted/MP08/original.zip)|[trace](traces/nanobot/MP08/original.zip)|
|MP09|[trace](traces/codex/MP09/original.zip)|[trace](traces/dsh/MP09/original.zip)|[trace](traces/opencode/MP09/original.zip)|[trace](traces/langgraph/MP09/original.zip)|[trace](traces/latte-planning-adapted/MP09/original.zip)|[trace](traces/nanobot/MP09/original.zip)|
|MP10|[trace](traces/codex/MP10/original.zip)|[trace](traces/dsh/MP10/original.zip)|[trace](traces/opencode/MP10/original.zip)|[trace](traces/langgraph/MP10/original.zip)|[trace](traces/latte-planning-adapted/MP10/original.zip)|[trace](traces/nanobot/MP10/original.zip)|
|MP12|[trace](traces/codex/MP12/original.zip)|[trace](traces/dsh/MP12/original.zip)|[trace](traces/opencode/MP12/original.zip)|[trace](traces/langgraph/MP12/original.zip)|[trace](traces/latte-planning-adapted/MP12/original.zip)|[trace](traces/nanobot/MP12/original.zip)|
|MP13|[trace](traces/codex/MP13/original.zip)|[trace](traces/dsh/MP13/original.zip)|[trace](traces/opencode/MP13/original.zip)|[trace](traces/langgraph/MP13/original.zip)|[trace](traces/latte-planning-adapted/MP13/original.zip)|[trace](traces/nanobot/MP13/original.zip)|
|MP14|[trace](traces/codex/MP14/original.zip)|[trace](traces/dsh/MP14/original.zip)|[trace](traces/opencode/MP14/original.zip)|[trace](traces/langgraph/MP14/original.zip)|[trace](traces/latte-planning-adapted/MP14/original.zip)|[trace](traces/nanobot/MP14/original.zip)|
|MP15|[trace](traces/codex/MP15/original.zip)|[trace](traces/dsh/MP15/original.zip)|[trace](traces/opencode/MP15/original.zip)|[trace](traces/langgraph/MP15/original.zip)|[trace](traces/latte-planning-adapted/MP15/original.zip)|[trace](traces/nanobot/MP15/original.zip)|
|MP16|[trace](traces/codex/MP16/original.zip)|[trace](traces/dsh/MP16/original.zip)|[trace](traces/opencode/MP16/original.zip)|[trace](traces/langgraph/MP16/original.zip)|[trace](traces/latte-planning-adapted/MP16/original.zip)|[trace](traces/nanobot/MP16/original.zip)|
|MP17|[trace](traces/codex/MP17/original.zip)|[trace](traces/dsh/MP17/original.zip)|[trace](traces/opencode/MP17/original.zip)|[trace](traces/langgraph/MP17/original.zip)|[trace](traces/latte-planning-adapted/MP17/original.zip)|[trace](traces/nanobot/MP17/original.zip)|
|MP18|[trace](traces/codex/MP18/original.zip)|[trace](traces/dsh/MP18/original.zip)|[trace](traces/opencode/MP18/original.zip)|[trace](traces/langgraph/MP18/original.zip)|[trace](traces/latte-planning-adapted/MP18/original.zip)|[trace](traces/nanobot/MP18/original.zip)|
|MP19|[trace](traces/codex/MP19/original.zip)|[trace](traces/dsh/MP19/original.zip)|[trace](traces/opencode/MP19/original.zip)|[trace](traces/langgraph/MP19/original.zip)|[trace](traces/latte-planning-adapted/MP19/original.zip)|[trace](traces/nanobot/MP19/original.zip)|
|MP20|[trace](traces/codex/MP20/original.zip)|[trace](traces/dsh/MP20/original.zip)|[trace](traces/opencode/MP20/original.zip)|[trace](traces/langgraph/MP20/original.zip)|[trace](traces/latte-planning-adapted/MP20/original.zip)|[trace](traces/nanobot/MP20/original.zip)|
|MP21|[trace](traces/codex/MP21/original.zip)|[trace](traces/dsh/MP21/original.zip)|[trace](traces/opencode/MP21/original.zip)|[trace](traces/langgraph/MP21/original.zip)|[trace](traces/latte-planning-adapted/MP21/original.zip)|[trace](traces/nanobot/MP21/original.zip)|
|MP22|[trace](traces/codex/MP22/original.zip)|[trace](traces/dsh/MP22/original.zip)|[trace](traces/opencode/MP22/original.zip)|[trace](traces/langgraph/MP22/original.zip)|[trace](traces/latte-planning-adapted/MP22/original.zip)|[trace](traces/nanobot/MP22/original.zip)|
|MP23|[trace](traces/codex/MP23/original.zip)|[trace](traces/dsh/MP23/original.zip)|[trace](traces/opencode/MP23/original.zip)|[trace](traces/langgraph/MP23/original.zip)|[trace](traces/latte-planning-adapted/MP23/original.zip)|[trace](traces/nanobot/MP23/original.zip)|
|MP24|[trace](traces/codex/MP24/original.zip)|[trace](traces/dsh/MP24/original.zip)|[trace](traces/opencode/MP24/original.zip)|[trace](traces/langgraph/MP24/original.zip)|[trace](traces/latte-planning-adapted/MP24/original.zip)|[trace](traces/nanobot/MP24/original.zip)|
|MP25|[trace](traces/codex/MP25/original.zip)|[trace](traces/dsh/MP25/original.zip)|[trace](traces/opencode/MP25/original.zip)|[trace](traces/langgraph/MP25/original.zip)|[trace](traces/latte-planning-adapted/MP25/original.zip)|[trace](traces/nanobot/MP25/original.zip)|
|MP26|[trace](traces/codex/MP26/original.zip)|[trace](traces/dsh/MP26/original.zip)|[trace](traces/opencode/MP26/original.zip)|[trace](traces/langgraph/MP26/original.zip)|[trace](traces/latte-planning-adapted/MP26/original.zip)|[trace](traces/nanobot/MP26/original.zip)|
|MS02|[trace](traces/codex/MS02/original.zip)|[trace](traces/dsh/MS02/original.zip)|[trace](traces/opencode/MS02/original.zip)|[trace](traces/langgraph/MS02/original.zip)|[trace](traces/latte-planning-adapted/MS02/latte_ms02_rate_limit_retry.zip)|[trace](traces/nanobot/MS02/original.zip)|
|MS11|[trace](traces/codex/MS11/original.zip)|[trace](traces/dsh/MS11/original.zip)|[trace](traces/opencode/MS11/original.zip)|[trace](traces/langgraph/MS11/original.zip)|[trace](traces/latte-planning-adapted/MS11/latte_workspace_repair.zip)|[trace](traces/nanobot/MS11/original.zip)|
|MS12|[trace](traces/codex/MS12/original.zip)|[trace](traces/dsh/MS12/original.zip)|[trace](traces/opencode/MS12/original.zip)|[trace](traces/langgraph/MS12/original.zip)|[trace](traces/latte-planning-adapted/MS12/latte_workspace_repair.zip)|[trace](traces/nanobot/MS12/original.zip)|
|MS14|[trace](traces/codex/MS14/original.zip)|[trace](traces/dsh/MS14/original.zip)|[trace](traces/opencode/MS14/original.zip)|[trace](traces/langgraph/MS14/original.zip)|[trace](traces/latte-planning-adapted/MS14/latte_workspace_repair.zip)|[trace](traces/nanobot/MS14/original.zip)|
|MS23|[trace](traces/codex/MS23/original.zip)|[trace](traces/dsh/MS23/original.zip)|[trace](traces/opencode/MS23/original.zip)|[trace](traces/langgraph/MS23/original.zip)|[trace](traces/latte-planning-adapted/MS23/latte_workspace_repair.zip)|[trace](traces/nanobot/MS23/original.zip)|
|MS28|[trace](traces/codex/MS28/original.zip)|[trace](traces/dsh/MS28/original.zip)|[trace](traces/opencode/MS28/original.zip)|[trace](traces/langgraph/MS28/original.zip)|[trace](traces/latte-planning-adapted/MS28/latte_workspace_repair.zip)|[trace](traces/nanobot/MS28/original.zip)|
|MS29|[trace](traces/codex/MS29/original.zip)|[trace](traces/dsh/MS29/original.zip)|[trace](traces/opencode/MS29/original.zip)|[trace](traces/langgraph/MS29/original.zip)|[trace](traces/latte-planning-adapted/MS29/latte_workspace_repair.zip)|[trace](traces/nanobot/MS29/original.zip)|
|MS30|[trace](traces/codex/MS30/original.zip)|[trace](traces/dsh/MS30/original.zip)|[trace](traces/opencode/MS30/original.zip)|[trace](traces/langgraph/MS30/original.zip)|[trace](traces/latte-planning-adapted/MS30/latte_remaining_two_rate_limit_retry.zip)|[trace](traces/nanobot/MS30/original.zip)|
|MS41|[trace](traces/codex/MS41/original.zip)|[trace](traces/dsh/MS41/original.zip)|[trace](traces/opencode/MS41/original.zip)|[trace](traces/langgraph/MS41/original.zip)|[trace](traces/latte-planning-adapted/MS41/latte_workspace_repair.zip)|[trace](traces/nanobot/MS41/original.zip)|
|MS42|[trace](traces/codex/MS42/original.zip)|[trace](traces/dsh/MS42/original.zip)|[trace](traces/opencode/MS42/original.zip)|[trace](traces/langgraph/MS42/original.zip)|[trace](traces/latte-planning-adapted/MS42/latte_workspace_repair.zip)|[trace](traces/nanobot/MS42/original.zip)|
|N11|[trace](traces/codex/N11/original.zip)|[trace](traces/dsh/N11/original.zip)|[trace](traces/opencode/N11/original.zip)|[trace](traces/langgraph/N11/original.zip)|[trace](traces/latte-planning-adapted/N11/original.zip)|[trace](traces/nanobot/N11/original.zip)|
|N17|[trace](traces/codex/N17/original.zip)|[trace](traces/dsh/N17/original.zip)|[trace](traces/opencode/N17/original.zip)|[trace](traces/langgraph/N17/original.zip)|[trace](traces/latte-planning-adapted/N17/original.zip)|[trace](traces/nanobot/N17/original.zip)|
|N22|[trace](traces/codex/N22/original.zip)|[trace](traces/dsh/N22/original.zip)|[trace](traces/opencode/N22/original.zip)|[trace](traces/langgraph/N22/original.zip)|[trace](traces/latte-planning-adapted/N22/original.zip)|[trace](traces/nanobot/N22/original.zip)|
|N24|[trace](traces/codex/N24/original.zip)|[trace](traces/dsh/N24/original.zip)|[trace](traces/opencode/N24/original.zip)|[trace](traces/langgraph/N24/original.zip)|[trace](traces/latte-planning-adapted/N24/original.zip)|[trace](traces/nanobot/N24/original.zip)|

## 五个批次原件包

- [original](batches/original.zip)
- [opencode_git_repair](batches/opencode_git_repair.zip)
- [latte_workspace_repair](batches/latte_workspace_repair.zip)
- [latte_ms02_rate_limit_retry](batches/latte_ms02_rate_limit_retry.zip)
- [latte_remaining_two_rate_limit_retry](batches/latte_remaining_two_rate_limit_retry.zip)

## 解压与校验

每个ZIP独立可解压，无需拼接；SHA256SUMS逐包校验。case.json保存成员清单与哈希，trace-manifest.json记录394包和5个批次包的覆盖验证。报告中的local-artifacts://路径为脱敏后的来源标识，需要本地映射才可运行离线复算脚本；无需也不包含供应商密钥。
