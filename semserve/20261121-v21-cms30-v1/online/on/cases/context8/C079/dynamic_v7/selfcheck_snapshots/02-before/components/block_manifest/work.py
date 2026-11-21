def compute(payload):
    """返回 [kind,index,hex] 列表；若有缩略图则排首，再按块大小顺序切出文件块。"""
    file_hex = payload.get("file_hex", "")
    chunk_size = payload.get("chunk_size", 0)
    thumbnail_hex = payload.get("thumbnail_hex")
    result = []
    if thumbnail_hex is not None:
        result.append(["thumbnail", 0, thumbnail_hex])
    data = bytes.fromhex(file_hex)
    index = 0
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        result.append(["file", index, chunk.hex()])
        index += 1
    return result
