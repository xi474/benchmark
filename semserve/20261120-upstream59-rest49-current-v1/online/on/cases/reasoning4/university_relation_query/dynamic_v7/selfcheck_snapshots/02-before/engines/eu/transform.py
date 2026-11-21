import math


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_nonfinite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_nonfinite(v)


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    _reject_nonfinite(payloads)
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    departments = payload["departments"]
    professors = payload["professors"]
    eu = payload["eu"]

    country_by_dept = {}
    for d in departments:
        country_by_dept[d["id"]] = d["country"]

    eu_set = set(eu)
    ids = []
    for p in professors:
        for dept in p["departments"]:
            if country_by_dept[dept] in eu_set:
                ids.append(p["id"])
                break
    ids.sort()
    return {"name": contract["name"], "result": {"ids": ids}}
