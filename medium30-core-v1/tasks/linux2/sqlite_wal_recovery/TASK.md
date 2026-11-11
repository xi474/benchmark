# N23 损坏 WAL 的修复与数据合并

在 workspace 内按 README.md、各 SPEC.md 与 contract.json 完成组件。修复受控变换过的 SQLite WAL，使数据库可读取，并导出包含更新与新增记录的完整 JSON。

只实现公开业务范围，使用提供的正常输入与文件依赖；不要求额外通用边界防御。必须确保 check.py 成功、组件可从干净输入独立构建、最终产物语义正确，不修改受保护文件。
