def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    slots_payload = _unwrap(payloads[0])
    invitees_payload = _unwrap(payloads[1])
    supplies_payload = _unwrap(payloads[2])

    if not isinstance(slots_payload, dict):
        raise ValueError("slots must be object")
    if not isinstance(invitees_payload, dict):
        raise ValueError("invitees must be object")
    if not isinstance(supplies_payload, dict):
        raise ValueError("supplies must be object")

    slots = slots_payload.get("slots")
    complete = slots_payload.get("complete")
    if not isinstance(slots, list):
        raise ValueError("slots must be list")
    if not isinstance(complete, bool):
        raise ValueError("complete must be bool")

    members = invitees_payload.get("members")
    group_id = invitees_payload.get("group_id")
    if not isinstance(members, list):
        raise ValueError("members must be list")
    if not isinstance(group_id, str) or not group_id.strip():
        raise ValueError("group_id must be non-empty string")

    purchase = supplies_payload

    events = []
    notification = None
    if complete:
        if len(slots) < 2:
            raise ValueError("complete requires two slots")
        for i, slot in enumerate(slots[:2]):
            if not isinstance(slot, dict):
                raise ValueError("slot must be object")
            start = slot.get("start")
            end = slot.get("end")
            if not isinstance(start, int) or isinstance(start, bool):
                raise ValueError("slot start must be int")
            if not isinstance(end, int) or isinstance(end, bool):
                raise ValueError("slot end must be int")
            events.append({
                "id": group_id + "-" + str(i + 1),
                "start": start,
                "end": end,
                "members": list(members),
            })
        notification = {
            "group_id": group_id,
            "members": list(members),
            "event_ids": [e["id"] for e in events],
        }

    return {
        "name": contract["name"],
        "result": {
            "events": events,
            "notification": notification,
            "purchase": purchase,
        },
    }
