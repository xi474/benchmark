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
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")

    departments = data["departments"]
    professors = data["professors"]

    dept_country = {}
    for d in departments:
        dept_country[d["id"]] = d["country"]

    countries = {}
    for p in professors:
        cs = set()
        for dep in p["departments"]:
            cs.add(dept_country[dep])
        countries[p["id"]] = sorted(cs)

    return {"name": contract["name"], "result": {"countries": countries}}
