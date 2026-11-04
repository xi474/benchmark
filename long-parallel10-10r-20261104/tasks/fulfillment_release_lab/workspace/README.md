# 履约能力与采购承诺
        本工作区需要交付 loading, procurement, shipping 的决策实现、输入验证与结果审计。各组件的完整字段语义、目标优先级、边界和接口见 engines/组件/SPEC.md 与 contract.json。
        每个目录需要实现 model.py 的 normalize(payload)、solver.py 的 solve(payload, contract)、audit.py 的 verify(payload,result,contract)。可以在该目录增加私有辅助模块。audit 必须从输入与决策重算可行性和汇总量，不得无条件返回 True 或调用 solve 代替审计。
        提供的 render.py 调用这些 API 生成 outputs/组件.json；run_all.py 生成 outputs/final_report.json。不得修改 README、SPEC、contract、inputs、fixtures、check_module.py、render.py、run_all.py 和 check.py。
        局部检查：python3 engines/组件/check_module.py；完整检查：python3 check.py。跨文件导入可使用 from engines.组件名.model import normalize，所有入口会提供工作区根目录的 Python 路径。每次修改后请验证；公开样例不是完整规格，需结合可见契约补充独立边界检查。仅使用 Python 标准库。
