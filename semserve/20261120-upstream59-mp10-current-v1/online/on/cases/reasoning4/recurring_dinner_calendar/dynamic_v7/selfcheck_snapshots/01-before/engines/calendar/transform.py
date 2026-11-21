import copy
import re
from datetime import datetime, timedelta

_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


def _parse_time(s):
    if not isinstance(s, str) or not _TIME_RE.match(s):
        raise ValueError("invalid time")
    return datetime.strptime(s, "%Y-%m-%dT%H:%M")


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

    contacts = data.get("contacts")
    events = data.get("events")
    if not isinstance(contacts, list) or not isinstance(events, list):
        raise ValueError("contacts/events must be lists")

    # contacts: non-empty strings, no duplicates
    seen_contacts = set()
    for c in contacts:
        if not isinstance(c, str) or not c.strip():
            raise ValueError("invalid contact")
        if c in seen_contacts:
            raise ValueError("duplicate contact")
        seen_contacts.add(c)

    event_ids = set()
    normalized = []
    for ev in events:
        if not isinstance(ev, dict):
            raise ValueError("event must be object")
        eid = ev.get("id")
        start = ev.get("start")
        end = ev.get("end")
        kind = ev.get("kind")
        attendees = ev.get("attendees")
        if not isinstance(eid, str) or not eid.strip():
            raise ValueError("invalid event id")
        if eid in event_ids:
            raise ValueError("duplicate event id")
        event_ids.add(eid)
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("invalid kind")
        if not isinstance(attendees, list):
            raise ValueError("attendees must be list")
        s = _parse_time(start)
        e = _parse_time(end)
        if e <= s:
            raise ValueError("end must be after start")
        for a in attendees:
            if not isinstance(a, str) or a not in seen_contacts:
                raise ValueError("attendee not in contacts")
        dedup = sorted(set(attendees))
        normalized.append({
            "id": eid,
            "start": start,
            "end": end,
            "kind": kind,
            "attendees": dedup,
        })

    normalized.sort(key=lambda x: x["id"])

    existing_dinners = set()
    for ev in normalized:
        if ev["kind"] == "dinner" and ev["start"].endswith("T19:00"):
            existing_dinners.add(ev["start"][:10])

    existing_dinners = sorted(existing_dinners)

    return {
        "name": contract["name"],
        "result": {
            "events": normalized,
            "existing_dinners": existing_dinners,
        },
    }
