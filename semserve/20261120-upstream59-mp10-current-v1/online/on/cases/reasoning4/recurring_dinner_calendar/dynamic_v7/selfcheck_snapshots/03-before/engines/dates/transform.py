import datetime as _dt


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

    today = data.get("today")
    if not isinstance(today, str) or not today.strip():
        raise ValueError("today required")
    try:
        start = _dt.date.fromisoformat(today)
    except ValueError as exc:
        raise ValueError("invalid today") from exc

    # Monday is the first day of the week. The range ends on the Friday of the
    # next natural week (the week after the one containing `today`).
    weekday = start.weekday()  # Monday=0 ... Sunday=6
    days_to_next_friday = 11 - weekday
    end = start + _dt.timedelta(days=days_to_next_friday)

    dates = []
    cur = start
    while cur <= end:
        dates.append(cur.isoformat())
        cur += _dt.timedelta(days=1)

    return {"name": contract["name"], "result": {"dates": dates}}
