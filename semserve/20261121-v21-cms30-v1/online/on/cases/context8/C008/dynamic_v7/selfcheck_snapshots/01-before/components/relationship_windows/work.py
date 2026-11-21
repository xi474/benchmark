def compute(payload):
    """将链接和合并登记为 [起点,终点,生效时刻,失效时刻]。保留原顺序并补齐缺省区间。"""
    result = []
    for item in payload.get("links", []):
        result.append([
            item["a"],
            item["b"],
            item.get("from", 0),
            item.get("to", 10 ** 18),
        ])
    for item in payload.get("merges", []):
        result.append([
            item["a"],
            item["b"],
            item.get("from", 0),
            item.get("to", 10 ** 18),
        ])
    return result
