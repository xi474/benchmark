def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    ttl = payload["ttl"]
    events = payload["events"]

    # left: policy_decisions -> {str(index): bool} for request events
    # right: service_routes -> {str(index): [mode, available]} for request events

    replies = []
    authorizer_calls = 0
    service_lookups = 0
    remote_routes = 0
    certificates_issued = 0
    cert_counter = 0
    cache = {}  # (user, cluster, service) -> {"credential": ..., "expires": ...}

    for idx, event in enumerate(events):
        if event.get("op") != "request":
            continue
        key = str(idx)
        authorized = left.get(key, False)
        authorizer_calls += 1
        if not authorized:
            replies.append({"id": event["id"], "status": "denied"})
            continue

        mode, available = right.get(key, ["remote", False])
        service_lookups += 1
        if not available:
            replies.append({"id": event["id"], "status": "not_found"})
            continue

        now = event["time"]
        if mode == "local":
            replies.append({
                "id": event["id"],
                "status": "ok",
                "credential": "local",
                "route": "local",
            })
            continue

        # remote
        remote_routes += 1
        ck = (event["user"], event["cluster"], event["service"])
        entry = cache.get(ck)
        if entry is not None and entry["expires"] > now:
            credential = entry["credential"]
        else:
            # expired or missing -> issue new certificate
            cert_counter += 1
            certificates_issued += 1
            credential = "cert-%d" % cert_counter
            cache[ck] = {"credential": credential, "expires": now + ttl}
        replies.append({
            "id": event["id"],
            "status": "ok",
            "credential": credential,
            "route": "reverse_tunnel",
        })

    cache_list = [
        {
            "user": ck[0],
            "cluster": ck[1],
            "service": ck[2],
            "credential": entry["credential"],
            "expires": entry["expires"],
        }
        for ck, entry in sorted(cache.items())
    ]

    return {
        "replies": replies,
        "authorizer_calls": authorizer_calls,
        "service_lookups": service_lookups,
        "remote_routes": remote_routes,
        "certificates_issued": certificates_issued,
        "cache": cache_list,
    }
