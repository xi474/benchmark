# N26 双 KL 约束的概率分布构造

构造长度 150000 的正概率向量，使正向与反向 KL 到均匀分布都接近 10，并保存可独立读取的 dist.npy。

## 本版输入与业务范围

保留原题双KL目标和公开容差。正概率、归一化和有限KL是数学核心；不添加额外小数精度、唯一向量或固定优化器要求。

- `engines/probability_model`：返回 {n,groups,targets}。groups为三个正整数且和为n，第1组1个元素；构造分组常数概率可作为标准数值求根的低维参数化。targets={forward,backward}，本版均为10；n=150000。不要求指定算法或特定解。
- `engines/distribution`：构造长度model.n的正概率向量列表，和误差<=1e-5；KL(P||U)及KL(U||P)分别与targets误差<=0.001，使用自然对数。返回概率列表，允许任意合法解。可用预装NumPy/SciPy标准求根；无需GPU或训练。
- `engines/distribution_report`：返回 {size,mass,forward_kl,backward_kl,meets_target:bool}，必须从同一个概率向量实际重算；数值按公开容差验收而非精确字符串。

## 运行

仅修改各组件 engine.py，或添加私有辅助模块。README、SPEC、contract、输入、workflow、runtime、run_all、check、公开期望为受保护文件。

`python3 run_all.py` 依文件依赖运行；`python3 check.py` 重新执行公开例子。最终产物为 outputs/ 下的组件 JSON 和 final_report.json；contract.emit 声明的额外文件同属交付物。组件可并行开发；执行必须遵守绑定文件的先后关系。

公开例子不是完整验收。正式验收只覆盖本规格公开输入域、核心算法、必要状态、接口独立构建、最终产物和完整性。非核心稳健性不进入分数。核心用例全部通过不代表整题通过。Reward 上限事前冻结为2，50%部分进展+50%严格完整交付奖；可选稳健性另报。
