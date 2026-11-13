# 实测中档20题 v1

20道不同题、20个不同来源族，均完成Terminus 2 + DeepSeek V4 Pro普通模式五次有效运行及核心失败复核。每题严格通过2–3/5，作为固定基线/预算下的实测中档；ASCI结构标签单列。

17题来自DAG300原型启发/改编，3题项目自编；结构M 10题、H 10题。四类格式分布：context8 8题、linux2 1题、multistage4 1题、reasoning4 10题。

## 查阅入口

- [20题中文目录、来源、ASCI与结果](docs/20题目录.md)
- [20张DAG图与Mermaid](docs/DAG.md)
- [五次实测结果与统计口径](docs/五次实测结果.md)
- [来源与改编说明](docs/来源说明.md)
- [ASCI标准及提取说明](docs/ASCI评审.md)
- [核心失败复核](docs/核心失败复核.md)
- [冻结评分版本及装载兼容性](docs/评分版本说明.md)
- [机器可读完整索引](manifest.json)
- [Agent-only压缩包](downloads/agent-only.zip)

## 运行与评分

只把manifest中单题entry目录下的TASK.md与初始workspace交给Agent。将workspace作为工作目录，完成后使用外部评分器：

```sh
python tools/score_task.py --task M103 --workspace /path/to/finished/workspace --json-output /tmp/M103-score.json --reward-output /tmp/M103-reward.txt
```

该入口按task选择原批次冻结评分器，逐字节保存任务、输入、合同、verifier、参考实现和正式用例；没有把不同批次改成一个新判题器。每题核心用例数不同，原始分母保留。

任务权重均为2：reward = 2 × (0.5 × K/N + 0.5 × strict)。K/N为全部冻结verifier单元通过比例，strict为整题严格通过0/1；完整性违规reward归0。核心转换用例通过率另为KA/NA，不替代严格通过。

## 复现与边界

基线普通模式、每题五次、最多两并发、Agent 2CPU/3072MiB/3600秒、累计观测token上限200万；每批原协议、镜像和判题文件哈希保存在_authoring/history。正式算法/预算失败不重试，基础设施排除单列。此包不包含本机Docker镜像与API凭据。

datasets保存17个接纳子包及原SHA；原README/评审字节保留，历史本地链接可能不再适用，请使用本页发布索引。原20题筛选批等历史档案会提及未入选候选，正式范围仅manifest中的20项。

作者DAG、来源、ASCI、隐藏verifier、参考解及结果不属于Agent输入；仓库公开不等于允许将整仓库挂入Agent。Agent-only压缩包仅含TASK/初始workspace及中性文件哈希。

这些100次为开发校准与选题数据，经过中档筛选；论文正式harness比较应使用独立新试次。作者DAG表示潜在并行机会，不是实测并行加速，也不是唯一正确编排。

校验下载内容：`python -B tools/verify_integrity.py`。17个子包的SHA与原接纳记录逐字节核对；参见[发布验收](review/publication-validation.json)与[入口离线验收](review/dispatcher-validation.json)。

Windows较深目录下可对该仓库启用 git config core.longpaths true，或使用较短的检出路径。Agent-only包按tasks/ID组织，可直接解压使用。
