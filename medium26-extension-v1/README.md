# Medium26 extension v1

26个中等设计目标任务，93个核心组件，均为Python标准库、本地小型合成数据。任务由公开基准候选改造成本仓库已有的TASK.md + workspace格式。原14题与Mixed16 v4保持原有版本；本扩充包有独立manifest与seal。

## 四类结构

- multistage4：9题，domains/views承载领域解析与下游结果汇合。
- reasoning4：7题，engines承载标准算法、静态分析和有界状态规划。
- context8：5题，可导入package和受保护parser接口，修复跨接口兼容。
- linux2：5题，初始四文件，materialize后生成products及输入；不要求真实Linux、root或网络。

组件数按业务为3–5，未统一堆成同构节点，也没有按历史suite名字强制4/8个Agent。DAG由实际contract.inputs生成，位于_authoring/dags，仅供作者审查。任务难度与实际并行收益仍需模型实验校准。

## 入口

- [26题中文目录及DAG](docs/26题中文目录与DAG.md)
- [当前难度分级标准v1.1](docs/难度分级标准_v1.1.md)
- [来源与明确改造范围](NOTICE.md)
- [逐题原始来源与官方难度信息](docs/原题来源与难度标注.md)
- [作者验收结果](review/validation_report.json)
- [去重与结构审查](review/duplicate_audit.json)
- [26题Agent任务包](../medium26-extension-v1-agent.zip)

## 给Agent的材料

每次仅提供tasks/<suite>/<task>/TASK.md和对应初始workspace。不要将本扩充包整体、_authoring、verifier、review、DAG、参考解或其他任务挂载进Agent执行环境。合同中的输入文件接口是公开实现规范，Agent据此自行发现依赖。

Agent在工作区运行python3 check.py做本地冒烟。正式评分在可信评测环境运行：

```bash
python3 verifier/verify.py --entry reasoning4/grouped_feature_union --workspace /path/to/candidate/workspace
```

entry见manifest.json。正式验证包含受保护文件前后哈希、全部输出、不同输入的业务API、JSON加载器与render文件接口，不能用本地check替代。验证器需要与Agent可读写区域隔离；它不是恶意Python的系统沙箱。

## 复验与重建

Python>=3.11；验证器/参考算法/任务本身仅标准库。作者重新绘制PNG需要Pillow及中文字体，分发的PNG/SVG已预生成。

```bash
python3 _authoring/qa.py --root . --work /tmp/medium26-author-qa
python3 _authoring/build.py --dest /tmp/new-medium26
```

QA工作目录只放作者测试工作区，禁止当Agent输入。实验模型通过率/串并行提速未运行；作者参考解通过不是模型解题成绩。

manifest记录TASK与初始工作区哈希；workspace_tree_sha256按相对路径排序拼接path+NUL+文件sha256+LF再求SHA256。SHA256SUMS不包含自身、压缩包或Python缓存。Agent zip只含TASK及初始workspace，不含答案/隐藏向量。
