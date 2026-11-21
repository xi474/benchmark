def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    departments = payload["departments"]
    professors = payload["professors"]
    eu = payload["eu"]

    country_by_dept = {}
    for d in departments:
        country_by_dept[d["id"]] = d["country"]

    eu_set = set(eu)
    ids = []
    for p in professors:
        for dept in p["departments"]:
            if country_by_dept[dept] in eu_set:
                ids.append(p["id"])
                break
    ids.sort()
    return {"name": contract["name"], "result": {"ids": ids}}
