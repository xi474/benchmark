def compute(payload):
    """输出 [信号历史,该完整叶的权重或 null]，去重生成所有非空前缀，按历史字典序排列。"""
    scenarios = payload["scenarios"]
    # 每条完整路径不同，因此完整信号序列唯一对应一个叶权重。
    leaf_weight = {tuple(s["signals"]): s["weight"] for s in scenarios}
    prefixes = set()
    for s in scenarios:
        signals = s["signals"]
        for i in range(1, len(signals) + 1):
            prefixes.add(tuple(signals[:i]))
    result = []
    for p in sorted(prefixes):
        result.append([list(p), leaf_weight.get(p)])
    return result
