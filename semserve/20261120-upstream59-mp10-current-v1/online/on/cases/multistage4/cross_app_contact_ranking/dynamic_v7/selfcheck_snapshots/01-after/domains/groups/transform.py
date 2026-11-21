def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]

    contacts = data["contacts"]
    self_id = data["self_id"]
    keyword = data["keyword"]
    groups = data["groups"]

    contact_ids = {c["id"] for c in contacts}
    if self_id not in contact_ids:
        raise ValueError("self_id not in contacts")

    kw = keyword.casefold()
    ids = set()
    for g in groups:
        members = g["members"]
        for m in members:
            if m not in contact_ids:
                raise ValueError("unknown member")
        if any(msg.casefold().find(kw) >= 0 for msg in g["messages"]):
            for m in members:
                if m != self_id:
                    ids.add(m)

    return {"name": contract["name"], "result": {"ids": sorted(ids)}}
