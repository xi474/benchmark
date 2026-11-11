# 并行预测器数据入口 v1

本导出对应[medium30-core-v1](../medium30-core-v1/README.md)全部30题、94个业务组件。原题面、输入、SPEC、contract、workflow、参考解和正式verifier均在该完整数据集目录；本目录给出机器可读索引和静态执行标签，不删减原题信息。

## 文件

- tasks.jsonl：任务、组件ID与完整题目文件路径。
- components.jsonl：完整组件规格、contract、读写文件和直接依赖。
- graphs.jsonl / dependency_edges.jsonl：组件文件依赖DAG和每条边的输入绑定证据。
- pair_labels.jsonl：每对组件的先后关系与文件契约是否允许并行。A/B按组件名排序，不按拓扑序排列，避免标签被位置直接暴露。
- ready_states.jsonl：对DAG所有合法已完成集合推导的执行就绪集。
- text_features.jsonl：只保留任务文本与两个组件的业务规格，按pair_id连接标签；排除了显式bindings/output/depends字段。
- validation.json：JSONL联结、路径、DAG和正式验收向量的数据绑定检查。
- parallel-pipeline-validation.json：用两进程按导出的DAG运行30题参考实现，逐题检查组件结果、额外产物和受保护文件；全部通过。这是参考解组件执行检查，不是Agent实测或加速比。

## 获取全部信息

- [完整任务、规格、输入、来源、参考解和verifier](../medium30-core-v1/README.md)
- [全部30题的实际DAG图](../medium30-core-v1/docs/30题目录与实际DAG.md)
- [完整题包ZIP](../medium30-core-v1-full.zip)、[Agent初始包ZIP](../medium30-core-v1-agent.zip)、[Harbor执行包ZIP](../medium30-core-v1-harbor.zip)、[本预测器补充包ZIP](../medium30-parallel-prediction-v1.zip)

将本目录与medium30-core-v1放在同一父目录。重新导出：`python export_prediction.py --package ../medium30-core-v1 --output .`。参考解并行检查：`python validate_parallel_pipeline.py --package ../medium30-core-v1 --export . --output parallel-pipeline-validation.json`，使用与任务一致的Linux Python3.12/Git/NumPy/SciPy环境。

## 训练口径

标签描述“模块产物执行依赖”：A_before_B表示执行B需要A的产物。它不表示写B的代码必须等A完成；编码并行策略需要独立标注。parallel_permitted_by_file_contract只表示声明的文件契约允许并行，不是所有可能实现的线程安全保证，也不是实测加速比。

graphs、components中的dependencies、workflow、contract.bindings直接含有标签真值。若预测目标就是这些依赖，不应把这些字段直接用作模型输入；完整信息保留用于出题、核验和其他预测任务。text_features只是一个可选文本输入视图，最终输入定义由训练方确定。

ready_states由同一DAG推导，并非新的独立实测样本或Agent动作轨迹。训练/验证/测试至少按task_id分组，建议进一步按来源/算法家族分组，避免同题组件对随机拆分造成泄漏。30题、102个组件对适合先验证数据管道；不能据此声称大规模泛化能力。

所有路径相对medium30-core-v1数据集根；读取JSONL请使用UTF-8。标签版本为parallel-contract-export-v1。任务和评分规则未因导出而改变。
