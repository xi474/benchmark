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

    records = payload["records"]
    vocabulary = payload["vocabulary"]

    groups = {}
    for rec in records:
        key = rec["key"]
        category = rec["category"]
        if category is None:
            continue
        if not isinstance(category, str):
            raise ValueError("category must be str or null")
        groups.setdefault(key, set()).add(category)

    rows = []
    for key in sorted(groups):
        present = groups[key]
        values = {word: (word in present) for word in vocabulary}
        rows.append({"key": key, "values": values})

    return {"name": contract["name"], "result": {"rows": rows}}
