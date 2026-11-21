def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    plan = _unwrap(payloads[0])
    if not isinstance(plan, dict):
        raise ValueError("input must be object")

    snapshots = plan.get("snapshots")
    if not isinstance(snapshots, list):
        raise ValueError("snapshots must be list")

    # Map each contact to the set of cancelled event ids they attended.
    by_contact = {}
    for ev in snapshots:
        if not isinstance(ev, dict):
            raise ValueError("snapshot must be object")
        attendees = ev.get("attendees")
        eid = ev.get("id")
        if not isinstance(attendees, list):
            raise ValueError("attendees must be list")
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError("invalid event id")
        for contact in attendees:
            if not isinstance(contact, str) or not contact.strip():
                raise ValueError("invalid contact")
            by_contact.setdefault(contact, set()).add(eid)

    outbox = []
    for contact in sorted(by_contact):
        outbox.append({
            "to": contact,
            "event_ids": sorted(by_contact[contact]),
        })

    return {"name": contract["name"], "result": {"outbox": outbox}}
