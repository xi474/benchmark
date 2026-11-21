import math


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]

    records = payload["records"]

    groups = {}
    for record in records:
        key = record["key"]
        value = record["value"]
        entry = groups.setdefault(key, {"count": 0, "sum": 0})
        if value is None:
            continue
        if not _is_finite_number(value):
            raise ValueError("value must be finite number or null")
        entry["count"] += 1
        entry["sum"] += value

    rows = []
    for key in sorted(groups):
        entry = groups[key]
        count = entry["count"]
        total = entry["sum"]
        mean = total / count if count else None
        rows.append(
            {
                "key": key,
                "values": {"count": count, "sum": total, "mean": mean},
            }
        )

    return {"name": contract["name"], "result": {"rows": rows}}
