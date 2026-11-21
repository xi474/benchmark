import math


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, list):
        for item in obj:
            _reject_non_finite(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            _reject_non_finite(value)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    _reject_non_finite(payload)

    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    groups = {}
    for rec in records:
        if not isinstance(rec, dict):
            raise ValueError("record must be object")
        key = rec.get("key")
        if not isinstance(key, str):
            raise ValueError("key must be string")
        t = rec.get("time")
        if t is None:
            continue
        if isinstance(t, bool) or not isinstance(t, int):
            raise ValueError("time must be integer or null")
        groups.setdefault(key, []).append(t)

    rows = []
    for key in sorted(groups):
        times = groups[key]
        first = min(times)
        last = max(times)
        rows.append({
            "key": key,
            "values": {"first": first, "last": last, "span": last - first},
        })

    return {"name": contract["name"], "result": {"rows": rows}}
