def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("input must be object")
    if "root" not in payload or "nodes" not in payload:
        raise ValueError("missing root/nodes")
    root = payload["root"]
    nodes = payload["nodes"]
    if not isinstance(nodes, list):
        raise ValueError("nodes must be list")

    node_map = {}
    for n in nodes:
        if not isinstance(n, dict):
            raise ValueError("node must be object")
        if "id" not in n:
            raise ValueError("node missing id")
        nid = n["id"]
        if nid in node_map:
            raise ValueError("duplicate node id")
        node_map[nid] = n

    if root not in node_map:
        raise ValueError("root not found")

    # validate basic fields of all nodes
    for n in nodes:
        for k in ("id", "type", "message"):
            if k not in n:
                raise ValueError("node missing %s" % k)
        if not isinstance(n["id"], str) or not n["id"].strip():
            raise ValueError("bad id")
        if not isinstance(n["type"], str) or not n["type"].strip():
            raise ValueError("bad type")
        if not isinstance(n["message"], str):
            raise ValueError("bad message")
        if "cause" not in n or "context" not in n:
            raise ValueError("node missing cause/context")
        if n["cause"] is not None and not isinstance(n["cause"], str):
            raise ValueError("bad cause")
        if n["context"] is not None and not isinstance(n["context"], str):
            raise ValueError("bad context")
        if "suppress_context" not in n:
            raise ValueError("node missing suppress_context")
        if not isinstance(n["suppress_context"], bool):
            raise ValueError("bad suppress_context")
        if "frames" not in n:
            raise ValueError("node missing frames")
        if not isinstance(n["frames"], list):
            raise ValueError("bad frames")

    # follow chain from root
    chain = []
    seen = set()
    cur = root
    while True:
        if cur in seen:
            raise ValueError("cycle detected")
        seen.add(cur)
        if len(chain) >= 8:
            raise ValueError("chain too long")
        n = node_map[cur]
        chain.append(n)
        cause = n["cause"]
        if cause is not None:
            if cause not in node_map:
                raise ValueError("cause not found")
            cur = cause
            continue
        if not n["suppress_context"] and n["context"] is not None:
            ctx = n["context"]
            if ctx not in node_map:
                raise ValueError("context not found")
            cur = ctx
            continue
        break

    # chain is from root to innermost; reverse to innermost->root
    chain.reverse()
    result = []
    for i, n in enumerate(chain):
        if i == 0:
            link = None
        else:
            prev = chain[i - 1]
            if n["cause"] == prev["id"]:
                link = "cause"
            elif n["context"] == prev["id"]:
                link = "context"
            else:
                link = None
        result.append({
            "id": n["id"],
            "type": n["type"],
            "message": n["message"],
            "link": link,
        })

    return {"name": contract["name"], "result": {"chain": result}}
