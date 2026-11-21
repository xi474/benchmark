def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]

    departments = data["departments"]
    professors = data["professors"]

    dept_country = {}
    for d in departments:
        dept_country[d["id"]] = d["country"]

    countries = {}
    for p in professors:
        cs = set()
        for dep in p["departments"]:
            cs.add(dept_country[dep])
        countries[p["id"]] = sorted(cs)

    return {"name": contract["name"], "result": {"countries": countries}}
