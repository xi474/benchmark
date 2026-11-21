def compute(payload):
    """将链接和合并登记为 [起点,终点,生效时刻,失效时刻]。保留原顺序并补齐缺省区间。"""
    DEFAULT_FROM = 0
    DEFAULT_TO = 10 ** 18
    out = []
    for rel in payload.get("links", []):
        out.append([
            rel["a"],
            rel["b"],
            rel.get("from", DEFAULT_FROM),
            rel.get("to", DEFAULT_TO),
        ])
    for rel in payload.get("merges", []):
        out.append([
            rel["a"],
            rel["b"],
            rel.get("from", DEFAULT_FROM),
            rel.get("to", DEFAULT_TO),
        ])
    return out
