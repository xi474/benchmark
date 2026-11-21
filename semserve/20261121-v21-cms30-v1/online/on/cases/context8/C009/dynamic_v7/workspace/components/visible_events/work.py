def compute(payload):
    """返回按可见时刻及事件 ID 排序的业务事件。"""
    events = payload["events"]
    return sorted(events, key=lambda e: (e["visible"], e["id"]))
