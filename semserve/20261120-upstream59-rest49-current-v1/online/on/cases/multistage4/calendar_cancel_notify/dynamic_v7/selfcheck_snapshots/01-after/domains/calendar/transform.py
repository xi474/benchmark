def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    events = payload.get("events")
    day = payload.get("day")
    contacts = payload.get("contacts")
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    if isinstance(day, bool) or not isinstance(day, int):
        raise ValueError("day must be an int")
    if day < 0:
        raise ValueError("day must be >= 0")
    if not isinstance(contacts, list):
        raise ValueError("contacts must be a list")

    contact_ids = set()
    for c in contacts:
        if not isinstance(c, dict):
            raise ValueError("contact must be an object")
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("contact id must be non-empty str")
        if cid in contact_ids:
            raise ValueError("duplicate contact id")
        contact_ids.add(cid)

    lo = day * 1440
    hi = day * 1440 + 720

    cancelled = []
    snapshots = {}
    remaining = {}
    seen_ids = set()
    for e in events:
        if not isinstance(e, dict):
            raise ValueError("event must be an object")
        eid = e.get("id")
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError("event id must be non-empty str")
        if eid in seen_ids:
            raise ValueError("duplicate event id")
        seen_ids.add(eid)

        start = e.get("start")
        end = e.get("end")
        social = e.get("social")
        cancelled_flag = e.get("cancelled")
        attendees = e.get("attendees")

        if isinstance(start, bool) or not isinstance(start, int):
            raise ValueError("start must be int")
        if isinstance(end, bool) or not isinstance(end, int):
            raise ValueError("end must be int")
        if not isinstance(social, bool):
            raise ValueError("social must be bool")
        if not isinstance(cancelled_flag, bool):
            raise ValueError("cancelled must be bool")
        if not isinstance(attendees, list):
            raise ValueError("attendees must be a list")
        for a in attendees:
            if not isinstance(a, str) or not a.strip():
                raise ValueError("attendee must be non-empty str")
            if a not in contact_ids:
                raise ValueError("unknown attendee")

        if end <= start:
            raise ValueError("end must be > start")

        if lo <= start < hi and social and not cancelled_flag:
            cancelled.append(eid)
            snapshots[eid] = e
        else:
            remaining[eid] = e

    cancelled.sort()
    return {
        "name": contract["name"],
        "result": {
            "cancelled": cancelled,
            "snapshots": {k: snapshots[k] for k in sorted(snapshots)},
            "remaining": {k: remaining[k] for k in sorted(remaining)},
        },
    }
