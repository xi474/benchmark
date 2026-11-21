def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]

    contacts = data["contacts"]
    self_id = data["self_id"]
    window = data["window"]
    events = data["events"]

    start, end = window
    if end <= start:
        raise ValueError("window end must be after start")

    contact_ids = {c["id"] for c in contacts}
    if self_id not in contact_ids:
        raise ValueError("self_id not in contacts")

    minutes = {c["id"]: 0 for c in contacts if c["id"] != self_id}

    for ev in events:
        if ev["end"] <= ev["start"]:
            raise ValueError("event end must be after start")
        attendees = ev["attendees"]
        if self_id not in attendees:
            continue
        # clip to half-open window
        s = max(ev["start"], start)
        e = min(ev["end"], end)
        if e <= s:
            continue
        duration = e - s
        seen = set()
        for a in attendees:
            if a == self_id or a in seen:
                continue
            seen.add(a)
            if a not in contact_ids:
                raise ValueError("unknown attendee")
            minutes[a] = minutes.get(a, 0) + duration

    return {"name": contract["name"], "result": {"minutes": minutes}}
