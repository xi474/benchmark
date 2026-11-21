def compute(payload):
    """按事件位置返回请求当时的 [集群模式,服务是否可用]；合并端负责授权优先和实际计数。"""
    clusters = payload["clusters"]
    events = payload["events"]
    result = {}
    services_state = {}
    for idx, event in enumerate(events):
        op = event.get("op")
        if op == "service":
            cluster = event.get("cluster")
            service = event.get("service")
            available = event.get("available", False)
            services_state.setdefault(cluster, {})[service] = bool(available)
            continue
        if op != "request":
            continue
        cluster = clusters.get(event["cluster"], {})
        mode = cluster.get("mode", "remote")
        services = cluster.get("services", {})
        # service events may have updated availability
        updated = services_state.get(event["cluster"], {}).get(event["service"])
        if updated is None:
            available = bool(services.get(event["service"], False))
        else:
            available = updated
        result[str(idx)] = [mode, available]
    return result
