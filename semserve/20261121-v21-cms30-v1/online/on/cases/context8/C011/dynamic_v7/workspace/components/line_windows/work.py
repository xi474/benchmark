def compute(payload):
    """按工单 ID 输出合格产线及可行起止窗口三元组，按产线及起点的原遍历顺序。"""
    orders = payload.get("orders", [])
    released = set(payload.get("released", []))
    routing = payload.get("routing", {})
    lines = payload.get("lines", [])
    wip = payload.get("wip", [])
    freeze = payload.get("freeze", 0)
    changeover = payload.get("changeover", 0)

    # 每条产线上所有 wip 的最大结束时间（wip 占据第一顺位）。
    wip_end = {}
    for w in wip:
        line = w["line"]
        end = w["end"]
        if line not in wip_end or end > wip_end[line]:
            wip_end[line] = end

    result = {}
    for order in orders:
        oid = order["id"]
        sku = order["sku"]
        qty = order["qty"]
        due = order["due"]
        if sku not in released:
            result[oid] = []
            continue
        r = routing.get(sku)
        if r is None:
            result[oid] = []
            continue
        duration = r["setup"] + r["per_unit"] * qty
        triples = []
        for line in lines:
            lid = line["id"]
            if sku not in line.get("qualified", []):
                continue
            min_start = freeze
            if lid in wip_end:
                min_start = max(min_start, wip_end[lid] + changeover)
            for (ws, we) in line.get("windows", []):
                # 区间 [start, start+duration) 须完整落入 [ws, we)。
                lo = max(min_start, ws)
                hi = min(we - duration, due - duration)
                for start in range(lo, hi + 1):
                    triples.append([lid, start, start + duration])
        result[oid] = triples
    return result
