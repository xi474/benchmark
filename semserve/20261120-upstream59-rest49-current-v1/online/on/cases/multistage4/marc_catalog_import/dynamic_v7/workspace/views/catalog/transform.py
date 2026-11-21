def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    names = _unwrap(payloads[0])
    languages = _unwrap(payloads[1])
    subjects = _unwrap(payloads[2])

    def index(records):
        result = {}
        for r in records:
            rid = r["id"]
            if rid in result:
                raise ValueError("duplicate record id")
            result[rid] = r
        return result

    names_idx = index(names["records"])
    langs_idx = index(languages["records"])
    subs_idx = index(subjects["records"])

    ids = set(names_idx)
    if set(langs_idx) != ids or set(subs_idx) != ids:
        raise ValueError("record id sets must match")

    records = []
    for rid in sorted(ids):
        records.append({
            "id": rid,
            "authors": names_idx[rid]["authors"],
            "titles": names_idx[rid]["titles"],
            "languages": langs_idx[rid]["languages"],
            "subjects": subs_idx[rid]["subjects"],
        })

    return {
        "name": contract["name"],
        "result": {"records": records, "record_count": len(records)},
    }
