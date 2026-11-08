# 六题独立修订集 · medium6-specfix-v2

本版独立分发MP04、MP08、MP09、MP10、MP11、MP24，共6题、21个核心组件，版本2.0.0。保留原任务ID及TASK.md + workspace格式；四类风格分别为multistage4 1题、linux2 1题、reasoning4 3题、context8 1题。

修复公开中间schema、排序约定和改编范围说明。业务算法、输入、contract、verifier检查向量及原奖励政策保持；这是题面和实际本地子集的对齐，不宣称补齐上游完整功能。原Medium26 v1和原280次基线保留。此包不新增六种题型，也不将总任务数56记为62。

## 阅读入口

- [六题目录与DAG](docs/六题中文目录与DAG.md)
- [逐题问题、修改原因及上游归因](docs/问题与修改原因汇总.md)
- [改编前来源和原始难度](docs/原题来源与难度标注.md)
- [参考解与负例验收](review/validation_report.json)
- [版本与评分兼容性](review/version_compatibility.json)
- [初始/参考解部分得分验收](review/partial_reward_validation.json)
- [仅Agent任务包](../medium6-specfix-v2-agent.zip)

## 执行与评分

Python>=3.11，仅标准库，无网络、GPU或真实账号依赖。每次仅将某题TASK.md和初始workspace提供给Agent；_authoring、verifier、review、DAG和其他题均放在工作区外。DAG由实际contract.inputs生成，仅供作者审查。

```bash
python3 verifier/verify.py --entry context8/dinner_contact_checkout --workspace /path/to/workspace
python3 verifier/partial_reward/score.py --benchmark-root . --task medium/MP10 --workspace /path/to/workspace
python3 _authoring/qa.py --root . --work /tmp/medium6-author-qa
python3 _authoring/build.py --dest /tmp/new-medium6
```

正式得分按通过的verifier数量计算，沿用冻结奖励政策；M字段仅为历史中等设计目标及奖励权重，不是新版实测难度。旧版六题各0/5不能自动继承到新版。新版固定Terminus 2 + DeepSeek V4 Pro普通模式，每题五次，独立保存30次复测记录。

验证器不是恶意代码沙箱，需要与Agent隔离。初始workspace不含参考解；作者QA通过不等于模型解题通过。重新绘制PNG需要Pillow和中文字体，预生成DAG已包含在包中。
