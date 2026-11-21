def compute(payload):
    """按 response 位置记录 [原因,到期时间]；失败优先于陈旧，延迟分别为 2000/1000，正常相应用 null。"""
    result = {}
    for index, event in enumerate(payload.get("events", [])):
        if event.get("op") != "response":
            continue
        if event.get("failed"):
            result[str(index)] = ["failure", event["time"] + 2000]
        elif event.get("stale") == 1:
            result[str(index)] = ["stale", event["time"] + 1000]
        else:
            result[str(index)] = None
    return result
