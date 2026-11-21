def compute(payload):
    """排除指向根的边，按 allowed 顺序返回节点下标对。"""
    nodes = payload["nodes"]
    allowed = payload["allowed"]
    root = payload["root"]
    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]
    result = []
    for parent, child in allowed:
        p = index[parent]
        c = index[child]
        if c != root_idx:
            result.append([p, c])
    return result
