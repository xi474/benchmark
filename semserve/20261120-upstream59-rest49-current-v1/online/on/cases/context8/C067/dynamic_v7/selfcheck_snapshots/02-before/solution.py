"""Implement the public business contract in TASK.md."""

import json


def load_payload(input_path):
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def transform(payload):
    ttl = payload["ttl"]
    clusters = payload["clusters"]
    policies = dict(payload["policies"])
    events = payload["events"]

    replies = []
    authorizer_calls = 0
    service_lookups = 0
    remote_routes = 0
    certificates_issued = 0
    cache = {}  # (user, cluster, service) -> {"credential": ..., "expires": ...}

    for event in events:
        op = event["op"]
        if op == "policy":
            policies[event["user"]] = event["allow"]
        elif op == "service":
            clusters[event["cluster"]]["services"][event["service"]] = event["available"]
        elif op == "request":
            authorizer_calls += 1
            user = event["user"]
            cluster = event["cluster"]
            service = event["service"]
            verb = event["verb"]
            now = event["time"]

            allowed = False
            for rule in policies.get(user, []):
                if rule["cluster"] != cluster or rule["verb"] != verb:
                    continue
                rs = rule.get("service")
                if rs is None or rs == "*" or rs == service:
                    allowed = True
                    break

            if not allowed:
                replies.append({"id": event["id"], "status": "denied"})
                continue

            service_lookups += 1
            cluster_info = clusters.get(cluster)
            services = cluster_info["services"] if cluster_info else {}
            if not services.get(service):
                replies.append({"id": event["id"], "status": "not_found"})
                continue

            mode = cluster_info["mode"]
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
            key = (user, cluster, service)
            entry = cache.get(key)
            if entry is not None and entry["expires"] > now:
                credential = entry["credential"]
            else:
                certificates_issued += 1
                credential = "cert-%d" % certificates_issued
                cache[key] = {"credential": credential, "expires": now + ttl}

            replies.append({
                "id": event["id"],
                "status": "ok",
                "credential": credential,
                "route": "reverse_tunnel",
            })

    cache_list = []
    for (user, cluster, service) in sorted(cache.keys()):
        entry = cache[(user, cluster, service)]
        cache_list.append({
            "user": user,
            "cluster": cluster,
            "service": service,
            "credential": entry["credential"],
            "expires": entry["expires"],
        })

    return {
        "replies": replies,
        "authorizer_calls": authorizer_calls,
        "service_lookups": service_lookups,
        "remote_routes": remote_routes,
        "certificates_issued": certificates_issued,
        "cache": cache_list,
    }


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
