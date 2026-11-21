# 多来源 YAML 注记、密文与模板读回

输入 sources 是按覆盖顺序的文档源序列，每份有 name、trusted、yaml。YAML 使用平面映射子集，每行恰为「key: value」（恰好一个空格），可有空行和独占一行的 --- 分文档。key 是小写字母，普通值为非空单行文本（以字母开头，可含空格和 ${key} 引用）。另一种值是 !vault 密文ID。普通值或 vault 值可在前面加 &名 和一个空格，后续同一文档可用 *名 引用。相同 key 的后定义覆盖；别名固定指向定义位置的值，跟随后续覆盖前的快照。名字无歧义，模板引用图无环且依赖存在。

每个最终条目记录 key 的声明来源、value 的原始来源，格式均为 [源名,1起行号,1起列号]；值从 key 冒号空格后的首字符定位（含 & 或 !），别名保留被引值原位置。tags 为 true 时 vault 按原密文导出，trusted 固定 false、render 值为 "[sealed]"。tags 为 false 时用 keys 中映射的明文替代，视作 trusted=true；如任一最终待导出 vault 无钥匙，则整次只返回 {"status":"sealed"}。普通值采用其定义来源的 trusted。render 对 trusted 普通值或已解封值递归把 ${key} 替换为最终覆盖视图中对应键的 render；不受信任普通值保持原文本。返回 {"status":"ok","entries":[[键,键来源,值来源,trusted,render],...],"dump":字符串}。entries 与 dump 按键升序。dump 每行写成 key: 后一个空格，vault 保留时多写 !vault 和空格，随后是原普通文本、密文ID或解封明文的 JSON 双引号字符串；以换行结束。dump 保存模板文本，render 代表消费结果。

## 交付与自检

工作目录为 /app。实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。load_payload(path) 读取指定的 UTF-8 JSON。build_component(input_path, output_path) 在干净目录中读取、计算、写入并返回同一结果。可增加业务模块。命令行入口为 python run_all.py --input PATH --output PATH。运行 python public_check.py 可核对随包公开示例。公开输入和期望文件也是完整的接口示例。

工作环境支持 Python 标准库、NumPy、SciPy 和 cryptography。受保护文件在 contract.json 中列出。评测使用本题声明的业务输入与数值精度。

## 可独立运行的业务文件

本版已接好 `solution.py` 的三个公开入口。实现下列两个组件的 `compute(payload)` 和工作区根目录 `integration.py` 的 `combine(payload, left, right)`。left、right 按表中两行的顺序对应，两项工作可同时开展。整合端消费组件的业务值，并完成题面其余计算。

| 实现文件 | 返回值约定 | 独占的结果文件 |
|---|---|---|
| `components/trusted_bindings/work.py` | 解析受信任文档的覆盖和文档内锚点。每个有效键输出 [原源序号,声明位置,[值位置,文本,是否密文,来源是否可信]]；位置为 [源名,行,列]。 | `components/trusted_bindings/result.json` |
| `components/external_bindings/work.py` | 解析不受信任文档的覆盖和文档内锚点。每个有效键输出 [原源序号,声明位置,[值位置,文本,是否密文,来源是否可信]]；位置为 [源名,行,列]。 | `components/external_bindings/result.json` |

每个组件目录已有独立公开输入 `input.json`、样例结果 `expected.json` 及可覆写的 `result.json`。分别运行组件可落盘，汇总命令只读取两份已有结果。最终交付路径 `outputs/result.json` 也已预建。

```sh
python -B component_runtime.py check trusted_bindings
python -B component_runtime.py run trusted_bindings
python -B component_runtime.py check external_bindings
python -B component_runtime.py run external_bindings
python -B component_runtime.py join
python -B run_all.py --input public_input.json --output outputs/result.json
python -B public_check.py
```

默认组件样例与整题公开输入对应。处理另一个输入文件时，请在两个 run 命令和 join 命令上使用相同的 `--input PATH`。每次独立实验使用自己的题目工作区。组件样例仅供开发自检，正式评分继续使用整题的冻结用例。
