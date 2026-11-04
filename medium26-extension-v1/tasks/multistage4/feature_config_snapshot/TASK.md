# 特性配置的模式、附件与引用一致性

分别校验配置结构、转换嵌套附件并解析资源引用，只有语义一致时才构建可导出的配置快照。阅读工作区README.md和各组件contract.json，补齐缺失Python实现并从输入重新计算全部组件结果与最终报告。仅使用标准库，保持稳定接口，不得硬编码样例输出。

实现各组件model.py、transform.py、render.py以及run_all.py、final_report.py；根据实际文件接口确定执行条件。完成后运行python3 check.py。不得修改任务说明、README、输入、契约、检查器、integrate.py、稳定parser及适用的materialize.py。公开检查仅为冒烟，正式评分在工作区外进行。
