def compute(payload):
    """为有截止日的作业返回 [需求,合格时段 ID 升序数组]，先按原始时段和七天半开窗口筛选。"""
    slots = payload["slots"]
    slot_day = {sid: day for sid, day, _cap in slots}
    result = {}
    for aid, due, demand, serviceable in payload["assignments"]:
        if due is None:
            continue
        valid = []
        for sid in serviceable:
            day = slot_day.get(sid)
            if day is None:
                continue
            if due - 7 <= day < due:
                valid.append(sid)
        valid.sort()
        result[aid] = [demand, valid]
    return result
