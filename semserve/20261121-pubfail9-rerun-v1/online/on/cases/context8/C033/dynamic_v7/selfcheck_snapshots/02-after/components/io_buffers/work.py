def compute(payload):
    """返回 [文件名字节数组映射,标准输入字节数组]，未指定文件或 stdin 时为空。"""
    files = payload.get("files") or {}
    file_map = {name: list(bytes.fromhex(hexstr)) for name, hexstr in files.items()}
    stdin_hex = payload.get("stdin_hex")
    stdin_bytes = list(bytes.fromhex(stdin_hex)) if stdin_hex else []
    return [file_map, stdin_bytes]
