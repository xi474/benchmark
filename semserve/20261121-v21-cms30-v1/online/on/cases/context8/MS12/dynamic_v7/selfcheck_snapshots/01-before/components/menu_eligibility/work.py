def compute(payload):
    """每个到货信号映射至可供菜品 ID，保持 recipes 顺序，检查难度、原料可得性和过敏限制。"""
    recipes = payload["recipes"]
    groups = payload["groups"]
    delivery = payload["delivery"]

    # 任一群体禁用的配料集合
    banned = set()
    for _, _, banned_list, _ in groups:
        banned.update(banned_list)

    result = {}
    for signal, available in delivery.items():
        available_set = set(available)
        eligible = []
        for recipe in recipes:
            if recipe["difficulty"] > 4:
                continue
            ingredients = recipe["ingredients"]
            if any(ing in banned for ing in ingredients):
                continue
            if all(ing in available_set for ing in ingredients):
                eligible.append(recipe["id"])
        result[signal] = eligible
    return result
