# 独立六题核心版 v3

本版为adapted6-core-v3（3.0.0），包含MP04、MP08、MP09、MP10、MP11、MP24，共6题、21个业务组件，保留multistage4、reasoning4、context8、linux2四类组织风格。这是独立版本，不修改原26题发布或v2实验成绩，不增加新的题型数量。

业务算法、夹具、contract和串并行文件依赖保持。核心完成保留业务字段的合法性、标准JSON输入输出、稳定接口、正确业务结果、集成与受保护文件完整性。无关附加字段的递归NaN/Infinity拒绝单列为可选稳健性，不扣核心reward，不决定核心难度。

## 入口

- [六题规格与DAG](docs/六题中文目录与DAG.md)
- [重构范围、原因与指标](docs/核心与稳健性重构说明.md)
- [v3难度与reward规则](docs/难度分级标准_v3.md)
- [来源与改编前信息](docs/原题来源与难度标注.md)
- [核心参考解及负例验收](review/validation_report.json)
- [核心/稳健性独立验收](review/scoring_v3_validation.json)
- [仅Agent任务包](../adapted6-core-v3-agent.zip)

## 使用

只向Agent提供某题TASK.md及初始workspace。_authoring、verifier、DAG、来源材料和参考解均放在Agent工作区之外。Python>=3.11、标准库、本地合成数据，无网络/真实账号/GPU依赖。

```bash
# 核心正式验收
python3 verifier/verify.py --entry context8/dinner_contact_checkout --workspace /path/to/workspace
# 核心reward + 独立稳健性报告；reward文件仅写核心得分
python3 verifier/partial_reward/score.py --benchmark-root . --task core6/MP10 --workspace /path/to/workspace
# 可独立运行的稳健性诊断，不决定核心成败
python3 verifier/robustness.py --benchmark-root . --task core6/MP10 --workspace /path/to/workspace
```

难度按固定Terminus 2 + DeepSeek V4 Pro普通模式五次核心成功次数分档：4–5易、2–3中、0–1难。参考解检查或旧候选的离线重评不等于新题面模型复测。M只保留历史reward权重（上限2），不冒充新版实测档。

重建：python3 _authoring/build.py --dest /tmp/new-adapted6-v3；作者验收见_authoring/qa.py。绘制PNG需要Pillow和中文字体，任务与verifier只用标准库。验证器应在可信隔离环境执行，不是恶意代码沙箱。
