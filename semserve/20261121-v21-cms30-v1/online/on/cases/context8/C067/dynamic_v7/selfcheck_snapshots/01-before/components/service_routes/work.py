def compute(payload):
    """按事件位置返回请求当时的 [集群模式,服务是否可用]；合并端负责授权优先和实际计数。"""
    clusters = payload["clusters"]
    events = payload["events"]
    result = {}
    for idx, event in enumerate(events):
        if event.get("op") != "request":
            continue
        cluster = clusters.get(event["cluster"], {})
        mode = cluster.get("mode", "remote")
        services = cluster.get("services", {})
        available = bool(services.get(event["service"], False))
        result[str(idx)] = [mode, available]
    return result
