import math


def _check_finite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_finite(v)


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    for p in payloads:
        if not isinstance(p, dict):
            raise ValueError("payload must be an object")
        _check_finite(p)

    snapshot = _unwrap(payloads[0])
    groups = _unwrap(payloads[1])
    mail = _unwrap(payloads[2])
    calendar = _unwrap(payloads[3])

    contacts = snapshot["contacts"]
    ages = {c["id"]: c["age"] for c in contacts}

    candidate_ids = set(groups["ids"]) | set(mail["ids"])
    minutes_map = calendar["minutes"]

    rows = []
    for cid in candidate_ids:
        if cid not in ages:
            raise ValueError("unknown contact id")
        minutes = minutes_map.get(cid, 0)
        rows.append({"id": cid, "minutes": minutes, "age": ages[cid]})

    rows.sort(key=lambda r: (-r["minutes"], -r["age"], r["id"]))

    winner = rows[0]["id"] if rows else None
    return {"name": contract["name"], "result": {"ranking": rows, "winner": winner}}
