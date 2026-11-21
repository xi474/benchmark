def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    records = payload["records"]
    vocabulary = payload["vocabulary"]

    # group non-null categories by key
    groups = {}
    for rec in records:
        key = rec["key"]
        category = rec["category"]
        if category is None:
            continue
        if not isinstance(category, str):
            raise ValueError("category must be str or null")
        groups.setdefault(key, set()).add(category)

    rows = []
    for key in sorted(groups):
        present = groups[key]
        values = {word: (word in present) for word in vocabulary}
        rows.append({"key": key, "values": values})

    return {"name": contract["name"], "result": {"rows": rows}}
