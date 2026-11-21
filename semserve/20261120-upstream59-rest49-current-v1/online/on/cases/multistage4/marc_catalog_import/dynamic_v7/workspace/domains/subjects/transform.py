def _clean(text):
    parts = text.split()
    s = " ".join(parts)
    return s.strip(" \t\r\n/:,;")


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


_TAG_CATEGORY = {
    "600": "people",
    "610": "organizations",
    "611": "meetings",
    "630": "works",
    "650": "topics",
    "651": "places",
}


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    src = _unwrap(payloads[0])
    records = src["records"]

    out_records = []
    for rec in records:
        rid = rec["id"]
        fields = rec.get("fields", [])
        categories = {
            "people": {},
            "organizations": {},
            "meetings": {},
            "works": {},
            "topics": {},
            "places": {},
        }
        for f in fields:
            tag = f.get("tag")
            cat = _TAG_CATEGORY.get(tag)
            if cat is None:
                continue
            subfields = f.get("subfields", [])
            main_parts = []
            sub_parts = []
            for sf in subfields:
                code = sf.get("code")
                value = sf.get("value", "")
                if code in ("a", "b"):
                    main_parts.append(value)
                elif code in ("v", "x", "y", "z"):
                    sub_parts.append(_clean(value))
            main = _clean(" ".join(main_parts))
            full = main
            if sub_parts:
                full = main + " -- " + " -- ".join(sub_parts)
            categories[cat][full] = categories[cat].get(full, 0) + 1

        subjects = {}
        for cat in ("people", "organizations", "meetings", "works", "topics", "places"):
            items = [
                {"value": v, "count": c}
                for v, c in sorted(categories[cat].items())
            ]
            subjects[cat] = items

        out_records.append({"id": rid, "subjects": subjects})

    return {"name": contract["name"], "result": {"records": out_records}}
