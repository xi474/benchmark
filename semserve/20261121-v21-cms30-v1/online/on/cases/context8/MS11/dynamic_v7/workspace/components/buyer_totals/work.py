def compute(payload):
    """按买家 ID 汇总属于 Cameras 或 Electronics 的行金额，每行只计一次；无购买为零。"""
    buyers = payload["buyers"]
    totals = {b: 0 for b in buyers}
    for order in payload["orders"]:
        buyer = order["buyer"]
        for line in order["lines"]:
            categories, qty, unit_price = line
            if "Cameras" in categories or "Electronics" in categories:
                totals[buyer] += qty * unit_price
    return totals
