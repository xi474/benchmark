KEY_BYTES = {
    "Enter": b"\r",
    "C-c": b"\x03",
    "C-d": b"\x04",
    "C-u": b"\x15",
    "Tab": b"\x09",
    "Backspace": b"\x7f",
}


def compute(payload):
    """每步按 Linux 终端键表编码为连续字节，返回十六进制字符串列表。"""
    result = []
    for step in payload["steps"]:
        data = bytearray()
        for key in step["keys"]:
            if key in KEY_BYTES:
                data += KEY_BYTES[key]
            else:
                data += key.encode("utf-8")
        result.append(data.hex())
    return result
