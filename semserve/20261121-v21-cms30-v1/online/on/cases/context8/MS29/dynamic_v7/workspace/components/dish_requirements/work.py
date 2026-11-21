from itertools import combinations


def compute(payload):
    """返回合格的三类菜品组合及合并需求，格式 [菜品 ID 数组,原料到数量映射]，按菜品字典序枚举。"""
    dishes = payload["dishes"]
    max_difficulty = payload["max_difficulty"]

    qualified = [d for d in dishes if d[2] <= max_difficulty]

    results = []
    for combo in combinations(qualified, 3):
        categories = {d[1] for d in combo}
        if len(categories) != 3:
            continue
        ids = sorted(d[0] for d in combo)
        merged = {}
        for d in combo:
            for material, qty in d[3].items():
                merged[material] = merged.get(material, 0) + qty
        results.append([ids, merged])

    results.sort(key=lambda r: r[0])
    return results
