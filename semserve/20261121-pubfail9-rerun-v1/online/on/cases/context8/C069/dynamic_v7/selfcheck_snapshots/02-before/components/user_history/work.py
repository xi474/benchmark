import copy


def compute(payload):
    """记录各续期事件发生时的用户快照，重放 update_user 的 roles、traits；以原位置字符串为键。"""
    user = payload.get("user", {})
    events = payload.get("events", [])

    current = {
        "name": user.get("name"),
        "roles": list(user.get("roles", [])),
        "traits": copy.deepcopy(user.get("traits", {})),
    }

    result = {}
    for index, event in enumerate(events):
        op = event.get("op")
        if op == "update_user":
            if "roles" in event:
                current["roles"] = list(event["roles"])
            if "traits" in event:
                current["traits"] = copy.deepcopy(event["traits"])
        elif op == "renew":
            result[str(index)] = copy.deepcopy(current)

    return result
