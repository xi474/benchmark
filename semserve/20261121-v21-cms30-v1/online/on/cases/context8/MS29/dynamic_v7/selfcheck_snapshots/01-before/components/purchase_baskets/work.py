from itertools import product


def compute(payload):
    """输出所有限量采购篮 [总价,总件数,按排序后 offer 的购买数量向量]；按这三项升序排列。"""
    offers = payload["offers"]
    # offers 已按商品 ID 升序排列（题面要求按报价 ID 升序的购买数量向量）。
    # 为稳妥起见，按商品 ID 排序。
    offers = sorted(offers, key=lambda o: o[0])
    limits = [o[3] for o in offers]
    prices = [o[2] for o in offers]

    baskets = []
    for counts in product(*(range(lim + 1) for lim in limits)):
        total_cost = sum(c * p for c, p in zip(counts, prices))
        total_items = sum(counts)
        baskets.append([total_cost, total_items, list(counts)])

    baskets.sort(key=lambda b: (b[0], b[1], b[2]))
    return baskets
