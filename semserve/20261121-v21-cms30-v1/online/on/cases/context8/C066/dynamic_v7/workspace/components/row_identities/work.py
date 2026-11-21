def compute(payload):
    """按事务、语句生成被消费旧主键的去重有序数组，I 不消耗旧主键。"""
    txs = payload["txs"]
    result = []
    for tx in txs:
        tx_result = []
        for statement in tx["statements"]:
            keys = []
            for change in statement:
                if change["op"] in ("U", "D"):
                    keys.append(change["old"])
            tx_result.append(sorted(set(keys)))
        result.append(tx_result)
    return result
