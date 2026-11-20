# 节日照片迁移后发送与缺失报告

处理已限定目标年份并附节日标注的照片元数据，按所需节日分类、迁移，再用新路径生成发送清单和缺失报告；本地子集不解析年份、不执行独立清理。阅读工作区README.md和各组件contract.json，补齐缺失Python实现并从输入重新计算全部组件结果与最终报告。仅使用标准库，保持稳定接口，不得硬编码样例输出。

实现各组件model.py、transform.py、render.py以及run_all.py、final_report.py；根据实际文件接口确定执行条件。完成后运行python3 check.py。不得修改任务说明、README、输入、契约、检查器、integrate.py、稳定parser及适用的materialize.py。公开检查仅为冒烟，正式评分在工作区外进行。

核心完成按业务算法、业务字段有效性、接口与集成结果判定。无关附加字段中的NaN/Infinity拒绝另作可选稳健性观测，不扣核心reward、不决定核心难度。
