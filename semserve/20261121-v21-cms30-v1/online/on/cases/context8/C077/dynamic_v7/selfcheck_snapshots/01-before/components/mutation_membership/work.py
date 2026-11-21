def compute(payload):
    """对 start/finish 事件按输入位置给出处理后仍活动的修改 ID 有序列表。"""
    events = payload.get("events", [])
    active = []
    result = {}
    for i, ev in enumerate(events):
        op = ev.get("op")
        if op == "start":
            mid = ev.get("id")
            if mid not in active:
                active.append(mid)
            result[str(i)] = list(active)
        elif op == "finish":
            mid = ev.get("id")
            if mid in active:
                active.remove(mid)
            result[str(i)] = list(active)
    return result
