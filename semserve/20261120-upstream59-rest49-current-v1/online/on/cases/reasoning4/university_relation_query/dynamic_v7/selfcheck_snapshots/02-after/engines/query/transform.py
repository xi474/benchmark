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

    raw = payloads[0]
    if isinstance(raw, dict) and set(raw) == {"name", "result"}:
        raw = raw["result"]
    if not isinstance(raw, dict):
        raise ValueError("payload must be an object")

    eu = payloads[1]
    if isinstance(eu, dict) and set(eu) == {"name", "result"}:
        eu = eu["result"]
    students = payloads[2]
    if isinstance(students, dict) and set(students) == {"name", "result"}:
        students = students["result"]
    countries = payloads[3]
    if isinstance(countries, dict) and set(countries) == {"name", "result"}:
        countries = countries["result"]

    eligible_ids = set(eu["ids"])
    counts = students["counts"]
    country_map = countries["countries"]

    professors = []
    for pid in sorted(eligible_ids):
        eligible_departments = sorted(
            d for d in counts if counts[d] > 10 and d in _professor_departments(raw, pid)
        )
        if eligible_departments:
            professors.append({
                "id": pid,
                "countries": country_map.get(pid, []),
                "eligible_departments": eligible_departments,
            })

    return {"name": contract["name"], "result": {"professors": professors}}


def _professor_departments(raw, pid):
    for p in raw["professors"]:
        if p["id"] == pid:
            return set(p["departments"])
    return set()
