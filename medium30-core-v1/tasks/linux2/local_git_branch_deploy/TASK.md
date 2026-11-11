# N25 本地 Git 双分支自动部署

在 workspace 内按 README.md、各 SPEC.md 与 contract.json 完成组件。搭建本地 bare 仓库和 post-receive hook，将 main/dev 的内容各自部署到对应目录。

只实现公开业务范围，使用提供的正常输入与文件依赖；不要求额外通用边界防御。必须确保 check.py 成功、组件可从干净输入独立构建、最终产物语义正确，不修改受保护文件。
