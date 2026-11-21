import copy


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    calendar = _unwrap(payloads[0])
    plan = _unwrap(payloads[1])
    notifications = _unwrap(payloads[2])

    events = calendar["events"]
    cancelled = set(plan["cancelled"])
    added = plan["added"]
    outbox = notifications["outbox"]

    final_events = [copy.deepcopy(e) for e in events if e["id"] not in cancelled]
    final_events.extend(copy.deepcopy(added))
    final_events.sort(key=lambda e: e["id"])

    return {
        "name": contract["name"],
        "result": {
            "events": final_events,
            "outbox": copy.deepcopy(outbox),
        },
    }
