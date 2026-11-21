def compute(payload):
    """按工单 ID 输出递归展开后的基础物料需求映射。"""
    orders = payload.get("orders", [])
    bom = payload.get("bom", {})

    def expand(sku, qty, acc):
        if sku not in bom:
            acc[sku] = acc.get(sku, 0) + qty
            return
        for child, cqty in bom[sku].items():
            expand(child, qty * cqty, acc)

    result = {}
    for order in orders:
        acc = {}
        expand(order["sku"], order["qty"], acc)
        result[order["id"]] = acc
    return result
