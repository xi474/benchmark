from itertools import permutations


def compute(payload):
    """返回 [所有可行映射位掩码,旧标签到各新标签的掩码映射]；位序按新标签升序的排列枚举。"""
    rubrics = payload["rubrics"]
    old_labels = sorted(rubrics.keys())
    new_labels = sorted({n for ns in rubrics.values() for n in ns})

    total_mask = 0
    mask_map = {o: {n: 0 for n in new_labels} for o in old_labels}

    for idx, perm in enumerate(permutations(new_labels)):
        feasible = True
        for o, n in zip(old_labels, perm):
            if n not in rubrics[o]:
                feasible = False
                break
        if feasible:
            bit = 1 << idx
            total_mask |= bit
            for o, n in zip(old_labels, perm):
                mask_map[o][n] |= bit

    return [total_mask, mask_map]
