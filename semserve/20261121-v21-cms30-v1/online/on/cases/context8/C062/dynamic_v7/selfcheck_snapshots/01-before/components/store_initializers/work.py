def compute(payload):
    """对每个 open 事件按其原始位置（十进制字符串）建立初始状态，字段同最终 stores 项。"""
    result = {}
    for index, event in enumerate(payload["events"]):
        if event.get("op") != "open":
            continue
        result[str(index)] = {
            "backend": event["backend"],
            "state": "open",
            "job": None,
            "revision": event.get("revision", 0),
            "closed_at": None,
            "updates": 0,
        }
    return result
