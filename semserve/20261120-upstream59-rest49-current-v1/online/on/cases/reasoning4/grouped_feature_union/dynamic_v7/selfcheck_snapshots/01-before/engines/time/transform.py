def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
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
