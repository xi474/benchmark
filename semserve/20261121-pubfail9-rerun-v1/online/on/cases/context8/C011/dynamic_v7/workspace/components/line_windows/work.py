def compute(payload):
    """按工单 ID 输出合格产线及可行起止窗口三元组，按产线及起点的原遍历顺序。"""
    orders = payload.get("orders", [])
    released = set(payload.get("released", []))
    routing = payload.get("routing", {})
    lines = payload.get("lines", [])
    wip = payload.get("wip", [])
    freeze = payload.get("freeze", 0)
    changeover = payload.get("changeover", 0)

    # 每条产线上所有 wip 的结束时间，用于计算最早可排产起点。
    wip_end = {}
    for w in wip:
        line = w.get("line")
        end = w.get("end", 0)
        if line not in wip_end or end > wip_end[line]:
            wip_end[line] = end

    result = {}
    for order in orders:
        oid = order["id"]
        sku = order["sku"]
        qty = order["qty"]
        due = order["due"]
        r = routing.get(sku)
        if r is None:
            result[oid] = []
            continue
        duration = r.get("setup", 0) + r.get("per_unit", 0) * qty
        triples = []
        for line in lines:
            lid = line["id"]
            if sku not in line.get("qualified", []) or sku not in released:
                continue
            earliest = freeze
            if lid in wip_end:
                earliest = max(earliest, wip_end[lid] + changeover)
            for ws, we in line.get("windows", []):
                start = max(earliest, ws)
                while start + duration <= we and start + duration <= due:
                    triples.append([lid, start, start + duration])
                    start += 1
        result[oid] = triples
    return result
