def compute(payload):
    """返回去重并按三元组字典序排列的已有图事实。"""
    graph = payload.get("graph", [])
    seen = set()
    result = []
    for edge in graph:
        key = tuple(edge)
        if key not in seen:
            seen.add(key)
            result.append(list(edge))
    result.sort(key=lambda e: tuple(e))
    return result
