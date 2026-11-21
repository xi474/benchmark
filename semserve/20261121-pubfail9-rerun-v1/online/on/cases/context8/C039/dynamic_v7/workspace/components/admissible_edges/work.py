def compute(payload):
    """排除指向根的边，按 allowed 顺序返回节点下标对。"""
    nodes = payload["nodes"]
    allowed = payload["allowed"]
    root = payload["root"]
    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]
    result = []
    for parent, child in allowed:
        if index[child] == root_idx:
            continue
        result.append([index[parent], index[child]])
    return result
