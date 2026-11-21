import math
from datetime import date


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


def _parse_date(s):
    if not isinstance(s, str):
        raise ValueError("date must be string")
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise ValueError("invalid date") from e


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
    students = data["students"]
    as_of = _parse_date(data["as_of"])

    dept_ids = [d["id"] for d in departments]
    counts = {did: 0 for did in dept_ids}

    for student in students:
        sid = student["id"]
        seen = set()
        for enr in student["enrolments"]:
            dept = enr["department"]
            start = _parse_date(enr["start"])
            end = enr["end"]
            if end is not None:
                end = _parse_date(end)
                if end <= start:
                    raise ValueError("end must be after start")
            if start <= as_of and (end is None or as_of < end):
                key = (dept, sid)
                if key not in seen:
                    seen.add(key)
                    counts[dept] = counts.get(dept, 0) + 1

    return {"name": contract["name"], "result": {"counts": counts}}
