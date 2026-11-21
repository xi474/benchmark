import datetime


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = _unwrap(payloads[0])
    if not isinstance(data, dict):
        raise ValueError("input must be object")

    today = data["today"]
    weekday = data["weekday"]
    hour = data["hour"]
    guest_count = data["guest_count"]

    if isinstance(weekday, bool) or not isinstance(weekday, int):
        raise ValueError("weekday must be int")
    if not 0 <= weekday <= 6:
        raise ValueError("weekday out of range")
    if isinstance(hour, bool) or not isinstance(hour, int):
        raise ValueError("hour must be int")
    if not 0 <= hour <= 23:
        raise ValueError("hour out of range")
    if isinstance(guest_count, bool) or not isinstance(guest_count, int):
        raise ValueError("guest_count must be int")
    if guest_count < 1:
        raise ValueError("guest_count must be >= 1")

    d = datetime.date.fromisoformat(today)
    delta = (weekday - d.weekday()) % 7
    if delta == 0:
        delta = 7
    target = d + datetime.timedelta(days=delta)
    start = "%sT%02d:00" % (target.isoformat(), hour)

    return {"name": contract["name"], "result": {"start": start, "guest_count": guest_count}}
