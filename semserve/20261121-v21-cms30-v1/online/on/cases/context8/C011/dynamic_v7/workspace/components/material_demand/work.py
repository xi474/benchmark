def compute(payload):
    """按工单 ID 输出递归展开后的基础物料需求映射。"""
    orders = payload.get("orders", [])
    bom = payload.get("bom", {})

    def expand(sku, qty, acc):
        children = bom.get(sku)
        if not children:
            acc[sku] = acc.get(sku, 0) + qty
            return
        for child, per in children.items():
            expand(child, qty * per, acc)

    result = {}
    for order in orders:
        acc = {}
        expand(order["sku"], order["qty"], acc)
        result[order["id"]] = acc
    return result
