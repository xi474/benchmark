import copy
from datetime import datetime, timedelta


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def _parse_dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M")


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    days_payload = _unwrap(payloads[0])
    calendar_payload = _unwrap(payloads[1])

    dates = days_payload["dates"]
    events = calendar_payload["events"]
    existing_dinners = set(calendar_payload["existing_dinners"])

    # Build new dinner reminders for non-existing dates.
    added = []
    for d in dates:
        if d in existing_dinners:
            continue
        added.append({
            "id": "dinner-" + d,
            "start": d + "T19:00",
            "end": d + "T20:00",
            "kind": "dinner",
            "attendees": [],
        })

    # New IDs must not collide with any old event ID.
    old_ids = {e["id"] for e in events}
    for a in added:
        if a["id"] in old_ids:
            raise ValueError("new id conflicts with existing event")

    # Cancel old events whose half-open interval intersects any new reminder.
    cancelled = []
    snapshots = []
    for e in events:
        es = _parse_dt(e["start"])
        ee = _parse_dt(e["end"])
        conflict = False
        for a in added:
            ns = _parse_dt(a["start"])
            ne = _parse_dt(a["end"])
            # half-open [start, end): overlap if es < ne and ns < ee
            if es < ne and ns < ee:
                conflict = True
                break
        if conflict:
            cancelled.append(e["id"])
            snapshots.append(copy.deepcopy(e))

    cancelled.sort()
    snapshots.sort(key=lambda e: e["id"])
    added.sort(key=lambda e: e["start"])

    return {
        "name": contract["name"],
        "result": {
            "added": added,
            "cancelled": cancelled,
            "snapshots": snapshots,
        },
    }
