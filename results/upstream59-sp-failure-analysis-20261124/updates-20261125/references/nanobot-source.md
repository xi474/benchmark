# Nanobot 0.3.5 实验安装包与工具源码定位

59 题均保存了 0.3.5 的实际客户端请求快照。冻结的 Python 发行名为 `nanobot-ai`。本地归档记录的是安装包逐文件 SHA-256，尚未核实与整套字节完全相同的上游 Git 提交。持有该版本的读者可以按下列路径计算 SHA-256，再定位到对应定义。

逐题实际调用见[原生工具审计](../evidence/nanobot-tool-audit-59.json)，带重叠时间的原生批次见[原生区间审计](../evidence/nanobot-batches-59.json)。

<a id="filesystem"></a>

## 带行号的读取以及旧片段单文件替换

文件 `nanobot/agent/tools/filesystem.py`。定义 `ReadFileTool`（第 270 行）、`EditFileTool`（第 860 行）。SHA-256 为 `c4dacaae64d8b3eafe72a48d37ef3ab90773f4c324260e2019486b179bce1435`。

<a id="shell"></a>

## 命令执行、stderr 与退出状态

文件 `nanobot/agent/tools/shell.py`。定义 `ExecTool`（第 162 行）。SHA-256 为 `695b54ec3b60ba6e6285207374cc47f5f7b01e72c0d7298f506a97c5a5fb3314`。

<a id="apply_patch"></a>

## 结构化多文件补丁

文件 `nanobot/agent/tools/apply_patch.py`。定义 `ApplyPatchTool`（第 78 行）。SHA-256 为 `bb37381ffd39889cd6d7f757203bfce383925f20b6cb32cbe8f863eac53e08a8`。

<a id="search"></a>

## 文件发现及带附近上下文的文本搜索

文件 `nanobot/agent/tools/search.py`。定义 `FindFilesTool`（第 207 行）、`GrepTool`（第 503 行）。SHA-256 为 `c12f126a71605806c5477753b147f60311dd8af1dd4a9e4e90b5548727d62b67`。

<a id="file_state"></a>

## 按文件内容和已读状态决定是否回传相同正文

文件 `nanobot/agent/tools/file_state.py`。定义 `FileStates`（第 53 行）。SHA-256 为 `e5d859e8d5c32348af3e52aced3905935f46f913534c7da4ffd48d72d223efb4`。

<a id="execution"></a>

## 工具调用编组及执行

文件 `nanobot/agent/tools/execution.py`。定义 `execute_tool_calls`（第 56 行）、`_partition_tool_batches`（第 292 行）。SHA-256 为 `1f64b8cf51e67f9f5acdaa4053487d378ae72637323255821b1b70d9019bd077`。

<a id="nanobot_observed_runner"></a>

## 实验新增的分块写和单次写入大小检查

文件 `nanobot_observed_runner.py`。定义 `ChunkedWriteFileTool`（第 64 行）、`GuardedWriteFileTool`（第 122 行）。SHA-256 为 `de862c74be6c9230ee890834cf353034136edf27e936e0e6dab9ab803edb0d1d`。

这份文件由本次实验适配层提供，指纹按归档适配器计算。
