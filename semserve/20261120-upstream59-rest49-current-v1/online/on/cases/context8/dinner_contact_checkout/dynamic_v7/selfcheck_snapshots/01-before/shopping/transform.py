def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    snapshot = _unwrap(payloads[0])
    dinner = _unwrap(payloads[1])
    contact = _unwrap(payloads[2])

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be object")
    if not isinstance(dinner, dict):
        raise ValueError("dinner must be object")
    if not isinstance(contact, dict):
        raise ValueError("contact must be object")

    variants = snapshot["variants"]
    wanted = snapshot["wanted"]
    guest_count = dinner["guest_count"]
    start = dinner["start"]
    recipient = contact.get("contact_id")

    if not isinstance(variants, list):
        raise ValueError("variants must be list")
    if not isinstance(wanted, list):
        raise ValueError("wanted must be list")
    if isinstance(guest_count, bool) or not isinstance(guest_count, int):
        raise ValueError("guest_count must be int")
    if guest_count < 1:
        raise ValueError("guest_count must be >= 1")

    # kind -> wanted attributes (kind unique per spec)
    wanted_by_kind = {}
    for w in wanted:
        if not isinstance(w, dict):
            raise ValueError("wanted entry must be object")
        kind = w["kind"]
        if kind in wanted_by_kind:
            raise ValueError("duplicate kind in wanted")
        wanted_by_kind[kind] = w["attributes"]

    # group variants by kind
    variants_by_kind = {}
    for v in variants:
        if not isinstance(v, dict):
            raise ValueError("variant must be object")
        kind = v["kind"]
        variants_by_kind.setdefault(kind, []).append(v)

    items = []
    total_cents = 0
    unavailable = []

    for kind in sorted(wanted_by_kind):
        attrs = wanted_by_kind[kind]
        candidates = []
        for v in variants_by_kind.get(kind, []):
            if v["attributes"] == attrs and v["stock"] >= guest_count:
                candidates.append(v)
        if not candidates:
            unavailable.append(kind)
            continue
        best = min(candidates, key=lambda v: (v["price_cents"], v["id"]))
        items.append({"id": best["id"], "kind": kind, "quantity": guest_count})
        total_cents += best["price_cents"] * guest_count

    items.sort(key=lambda it: it["kind"])
    unavailable.sort()

    checkout = (len(unavailable) == 0) and (recipient is not None)

    result = {
        "items": items,
        "total_cents": total_cents,
        "checkout": checkout,
        "recipient": recipient,
        "start": start,
        "unavailable": unavailable,
    }

    return {"name": contract["name"], "result": result}
