def compute(payload):
    """每轮返回完成的逻辑路径，按深度先父后子，同深度维持输入顺序。"""
    result = []
    for scan in payload.get("scans", []):
        finish = scan.get("finish", [])
        # Depth is the number of '/' separators (mount name has depth 0).
        ordered = sorted(finish, key=lambda p: p.count("/"))
        result.append(ordered)
    return result
