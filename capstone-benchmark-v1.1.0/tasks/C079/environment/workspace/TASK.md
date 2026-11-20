# C079 真实加密块校验、重试与摘要提交

实现一个可独立导入和命令行运行的组件。核心接口`transform(payload)`返回下述JSON结果，不修改输入对象。`load_payload(input_path)`读取UTF8 JSON并返回对象；`build_component(input_path,output_path)`独立读取、计算并将结果写入UTF8 JSON，返回相同结果。三个入口都须在无旧产物的全新目录工作。

## 公开业务契约

输入session_key_hex为32字节AES密钥、base_nonce_hex为12字节非负nonce起点、file_hex、正chunk_size(字节)、max_retries(0..3)、可选thumbnail_hex、corrupt_attempts映射及environment标签。输入保证nonce累加不溢出；无无关畸形输入要求。按文件字节顺序分块，无缩略图时空文件不产生block；缩略图存在时即使空字节也最先处理。

使用AES-256-GCM，每次加密尝试使用(base_nonce整数+全局尝试序号)的12字节大端nonce，序号从0开始。AAD为UTF8 `thumbnail:0`或`file:N`。加密结果为标准ciphertext||16字节tag。每次加密后必须解密并与原文比较，不受environment或文件大小控制。corrupt_attempts[label]列出该块0起始尝试中需翻转加密结果最后一个字节最低位的序号，用来模拟传输位错。

每块最多1+max_retries次；失败仅第一次发verification_failed通知，后续重试换新nonce并重新加密，成功才发布该块。文件SHA256只提交成功文件块的原文字节，每块恰好一次，不含缩略图。耗尽后停止，不处理后续块并返回verification_failed，摘要为此前已成功文件前缀；成功则status=ok。

输出blocks按发布顺序，每项kind/index/nonce_hex/ciphertext_hex/plaintext_sha256；attempts按尝试顺序含block/attempt/verified；notifications每失败块至多一项block/error；failed_block为耗尽label或null，file_sha256为已提交原文摘要。加密块完整性是本题主业务，不是外围鲁棒性加分。

## 交付与公开检查

在`solution.py`实现三个入口；可自行新增业务文件。`python run_all.py --check`运行小型公开例。`python run_all.py --input public_input.json --output output.json`生成产物。运行不依赖作者目录、既有output、网络或隐藏服务；不得修改run_all.py、public_input.json和public_expected.json。验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。
