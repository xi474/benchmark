def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]

    contacts = data["contacts"]
    self_id = data["self_id"]
    keyword = data["keyword"]
    emails = data["emails"]

    contact_ids = {c["id"] for c in contacts}
    if self_id not in contact_ids:
        raise ValueError("unknown self_id")

    ids = set()
    for e in emails:
        sender = e["sender"]
        if sender not in contact_ids:
            raise ValueError("unknown sender")
        if sender == self_id:
            continue
        if keyword.casefold() in e["subject"].casefold():
            ids.add(sender)

    return {"name": contract["name"], "result": {"ids": sorted(ids)}}
