# 可中断的多挂载音乐库同步

nodes 描述只读虚拟目录图，每个节点有 files（文件名到稳定曲目id）、dirs（子目录名到节点id）、ignore（当前目录精确忽略的条目名）。同一节点可挂到不同逻辑位置，目录图无环。mounts 将顶层挂载名映射到节点id。逻辑路径以挂载名开始，用 / 相连。initial 是上次索引的 {逻辑文件路径:曲目id}，均属于这些挂载。scans 按顺序发生，每项含 replace（节点id到完整替换定义）和 finish（本次完成扫描的逻辑目录路径列表，均在本次快照可达）。替换同时生效。可达性受所有祖先的 ignore 约束。
对 finish 中每个目录，本次扫描掌握其未忽略的直接文件与直接子目录的完整清单。直接文件按当前结果覆盖；旧索引若位于一个已消失或被忽略的直接条目之下（含文件与目录互换），清除该旧分支。当前仍可见但未完成扫描的子目录内部，保留旧索引。finish 外的目录不得推断删除。嵌套 finish 按同一快照解释。每次返回 {index,changed}，changed 包含该次前后路径集合有变化的曲目 id，每个值为 [排序的旧路径列表,排序的新路径列表]；同曲目可有多个别名。返回各次结果列表。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。
