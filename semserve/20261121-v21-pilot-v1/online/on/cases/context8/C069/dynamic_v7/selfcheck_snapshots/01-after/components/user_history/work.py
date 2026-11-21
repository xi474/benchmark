def compute(payload):
    """记录各续期事件发生时的用户快照，重放 update_user 的 roles、traits；以原位置字符串为键。"""
    events = payload.get("events", [])
    user = payload.get("user", {})
    current = {
        "name": user.get("name"),
        "roles": list(user.get("roles", [])),
        "traits": dict(user.get("traits", {})),
    }
    result = {}
    for i, ev in enumerate(events):
        op = ev.get("op")
        if op == "update_user":
            if "roles" in ev:
                current["roles"] = list(ev["roles"])
            if "traits" in ev:
                current["traits"] = dict(ev["traits"])
        elif op == "renew":
            result[str(i)] = {
                "name": current["name"],
                "roles": list(current["roles"]),
                "traits": dict(current["traits"]),
            }
    return result
