def compute(payload):
    """为每个 get 的原始位置生成 [若启动时的完成时刻,value,error]；只有命中未复用时才实际启动。"""
    events = payload["events"]
    result = {}
    for i, event in enumerate(events):
        if event.get("op") != "get":
            continue
        finished_at = event["time"] + event["delay"]
        value = event["value"]
        error = event.get("error", None)
        result[str(i)] = [finished_at, value, error]
    return result
