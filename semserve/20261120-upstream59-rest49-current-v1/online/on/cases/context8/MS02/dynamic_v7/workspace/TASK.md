# 文献综述主题分配与证据图更新

空主题表对应空综述及原图边的去重排序。

topics 是主题的固定顺序。papers 每项包含 id、methods（该论文有实质内容的章节名列表）和 claims（[主题,支撑章节,整数质量] 列表）。仅支撑章节列于本论文 methods 的候选可用；同题同论文保留最大质量。每主题必须选一篇，不得重用论文。依次最大化所有主题中的最低质量、总质量，再取论文ID序列字典序最小解。graph 为现有 [起点,关系,终点] 边，返回 {"review":[[主题,论文ID,质量],...],"graph":[...]}。后者是既有边与每条 [论文ID,"supports",主题] 的去重并集，按三项字典序排序。无完整分配返回 null。字符串比较按大小写原样，最多8主题12论文。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。
