# 带依赖批次的单次委派与重试回放

输入 tasks 是无序、无环的任务图，各项含 id、needs、pool、stream、attempts。pools[pool] 是循环选择的虚拟主机列表。feeds[主机][stream] 是循环产生批次的列表，每一批是整数数组；各 (主机,stream) 独立计数，非空列表。initial 为每台主机的初始整数事实值。所有池和流从索引0开始。每轮同时放行轮初全部已满足依赖的任务；同一轮对有状态选择器的消费，以任务 id 字典序为标准。每个任务在整个执行期只消费一次委派选择器和该主机上的一次批次选择器。attempts 为成功所需尝试次数；重试使用已选主机、批次及快照，之前尝试无提交。

每个任务读取轮初该主机事实值 base 和直接父任务的已提交 delta 之和 parent。批内每个 item 的业务结果为 (base+item)×(1+parent)；delta 为批结果之和。该轮所有成功提交结束后，各主机事实值一次性增加委派到其上的 delta 总和。输出 {"tasks":按id键控的 {host,items,base,parent,delta,attempts},"facts":最终主机值,"pool_reads":每个给出的池读取次数,"feed_reads":与 feeds 同形的主机→流→读取次数}。多个同轮任务可能分往同主机。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。
