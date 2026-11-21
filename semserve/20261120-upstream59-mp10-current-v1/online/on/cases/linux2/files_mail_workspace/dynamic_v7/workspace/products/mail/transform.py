import datetime
import math


def _reject_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number not allowed")
    if isinstance(value, dict):
        for v in value.values():
            _reject_nonfinite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_nonfinite(v)
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("input must be object")
    _reject_nonfinite(data)

    emails = data["emails"]
    month = data["month"]
    trash_keyword = data["trash_keyword"]

    try:
        datetime.date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError("invalid month")

    trash_ids = []
    for e in emails:
        if not isinstance(e, dict):
            raise ValueError("email must be object")
        date = e["date"]
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            raise ValueError("invalid date")
        if date.startswith(month) and trash_keyword.casefold() in e["subject"].casefold() and e["folder"] != "TRASH":
            trash_ids.append(e["id"])

    trash_ids.sort()
    return {"name": contract["name"], "result": {"trash_ids": trash_ids}}
