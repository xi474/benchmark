def compute(payload):
    """返回去重并按三元组字典序排列的已有图事实。"""
    graph = payload.get("graph", [])
    triples = [tuple(t) for t in graph]
    return [list(t) for t in sorted(set(triples))]
