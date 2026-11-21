def compute(payload):
    """按 get 驱动的 16×TTL 规则生成触发清理的 get 位置，以及下一次清理的时间。输出以位置字符串为键的映射。"""
    ttl = payload["ttl"]
    events = payload["events"]
    next_cleanup = 16 * ttl
    result = {}
    for i, ev in enumerate(events):
        if ev.get("op") == "get":
            now = ev["time"]
            if now >= next_cleanup:
                next_cleanup = now + 16 * ttl
                result[str(i)] = next_cleanup
    return result
