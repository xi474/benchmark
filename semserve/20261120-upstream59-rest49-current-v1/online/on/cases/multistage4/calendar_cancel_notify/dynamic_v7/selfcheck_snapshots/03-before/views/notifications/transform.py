import math


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_non_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_non_finite(v)


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    _reject_non_finite(payloads)
    _reject_non_finite(contract)

    cancel_result = payloads[0]
    channel_result = payloads[1]

    if not isinstance(cancel_result, dict):
        raise ValueError("cancel result must be an object")
    if not isinstance(channel_result, dict):
        raise ValueError("channel result must be an object")

    # Unwrap name/result envelope if present.
    if set(cancel_result) == {"name", "result"}:
        cancel_result = cancel_result["result"]
    if set(channel_result) == {"name", "result"}:
        channel_result = channel_result["result"]

    if not isinstance(cancel_result, dict):
        raise ValueError("cancel result must be an object")
    if not isinstance(channel_result, dict):
        raise ValueError("channel result must be an object")

    snapshots = cancel_result["snapshots"]
    cancelled_ids = sorted(cancel_result["cancelled"])
    contacts = channel_result["contacts"]

    # Union of attendees across target snapshots, deduplicated.
    member_set = set()
    for eid in cancelled_ids:
        snap = snapshots[eid]
        for cid in snap["attendees"]:
            if cid not in contacts:
                raise ValueError("unknown contact id: %s" % cid)
            member_set.add(cid)
    members = sorted(member_set)

    outbox = []
    unreachable = []
    message_members = []

    for cid in members:
        c = contacts[cid]
        email = c["email"]
        primary = c["primary"]
        address = c["address"]

        has_email = email is not None
        has_primary = primary is not None

        if has_email:
            outbox.append({
                "channel": "email",
                "to": email,
                "recipients": [cid],
                "requires": cancelled_ids,
            })
        if primary == "message":
            message_members.append(cid)
        elif primary == "chat":
            outbox.append({
                "channel": "chat",
                "to": address,
                "recipients": [cid],
                "requires": cancelled_ids,
            })
        elif primary is None:
            if not has_email:
                unreachable.append(cid)

    group = None
    if message_members:
        group = {
            "id": "cancelled-social",
            "members": message_members,
            "requires": cancelled_ids,
        }
        outbox.append({
            "channel": "message_group",
            "to": "cancelled-social",
            "recipients": message_members,
            "requires": cancelled_ids,
        })

    outbox.sort(key=lambda o: (o["channel"], o["to"]))
    unreachable.sort()

    return {
        "name": contract["name"],
        "result": {
            "outbox": outbox,
            "unreachable": unreachable,
            "group": group,
        },
    }
