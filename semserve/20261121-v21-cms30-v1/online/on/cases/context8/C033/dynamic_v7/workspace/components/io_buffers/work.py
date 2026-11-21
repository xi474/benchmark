def compute(payload):
    """返回 [文件名字节数组映射,标准输入字节数组]，未指定文件或 stdin 时为空。"""
    files = payload.get("files") or {}
    result_files = {}
    for name, hexstr in files.items():
        result_files[name] = list(bytes.fromhex(hexstr))
    stdin_hex = payload.get("stdin_hex")
    stdin_bytes = list(bytes.fromhex(stdin_hex)) if stdin_hex else []
    return [result_files, stdin_bytes]
