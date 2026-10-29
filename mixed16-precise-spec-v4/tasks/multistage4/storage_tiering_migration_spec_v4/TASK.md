# 存储分层迁移工具修复

完成随附 workspace 中缺失的 Python 实现：核验存储证据、生成风险排名与审核负载、计算迁移波次和关键路径，并交付集成报告。

业务语义以 README.md 的函数接口、字段定义及各目录 contract.json 为准。实现各组件 model.py、transform.py、render.py，以及根 run_all.py、final_report.py；仅使用 Python 标准库，从输入重新计算结果，禁止硬编码产物。

特别核对 README 中的 records 集合范围、证据评分公式、迁移波次的输入解释和最终摘要对象。根据现有文件接口自行确定可执行条件，不按目录或文件名猜测执行顺序。

完成后运行 python3 check.py。不得修改 README、输入、契约、检查脚本或 integrate.py；可见检查通过不等于外部正式验证通过。
