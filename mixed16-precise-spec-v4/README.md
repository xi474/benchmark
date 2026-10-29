# Mixed16 · 精确规格版 v4

16个任务，四类目录各4题；合并独立修订的storage_tiering_migration与其余15题。
本版本仅改动每题TASK.md与workspace/README.md，精确说明原有语义与边界。输入、契约、稳定接口、物化器、公开检查、参考算法、正式预期与隐藏API向量保留v3语义。

## 下载与Agent输入

[下载16题Agent任务包](mixed16-precise-spec-v4-agent.zip)。解压后为tasks/<suite>/<task_name>_spec_v4/。
每次只将该题TASK.md及workspace交给被测Agent。不要挂载本发布目录整体、trusted_validation或review；Agent包不含这些材料。
没有新增Agent调度DAG、并行标签、分支数、Offer触发位置或金标。业务算法中的图与契约的文件接口属于实现规范，不是运行时计划。

## 本地检查与正式评分

Agent在候选workspace运行python3 check.py；该命令只做本地冒烟，不能替代正式评分。
外部可信评测端保留trusted_validation，在Agent执行结束后运行：

```bash
python3 trusted_validation/verifier/verify.py --entry multistage4/storage_tiering_migration_spec_v4 --workspace /path/to/candidate/workspace
```

其他entry见manifest.json的entry_id/verification_entry_id。评测材料必须与Agent可读写范围隔离；外部verifier本身不是恶意Python的进程隔离器。
版本间README哈希不同，应使用本v4的seal，不能使用v3 seal给v4候选判分。

## 版本与校验

原始v3保留在同仓库mixed16-extension-v3。精确规格修订是新的任务描述实验条件，不能将与v3的执行差异全部归因于Runtime。
manifest.json记录16题的相对路径及任务/工作区哈希；SHA256SUMS覆盖发布文件（不含其自身）。
review/validation_report.json记录本次打包的离线一致性校验，review/task_changes.json列出每题修改范围。
这些校验不代表模型解题通过率；本发布不包含API密钥、执行trace、已解答workspace或模型实验结果。
