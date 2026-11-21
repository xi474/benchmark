def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    raw = payloads[0]
    if isinstance(raw, dict) and set(raw) == {"name", "result"}:
        raw = raw["result"]

    eu = payloads[1]
    if isinstance(eu, dict) and set(eu) == {"name", "result"}:
        eu = eu["result"]
    students = payloads[2]
    if isinstance(students, dict) and set(students) == {"name", "result"}:
        students = students["result"]
    countries = payloads[3]
    if isinstance(countries, dict) and set(countries) == {"name", "result"}:
        countries = countries["result"]

    eligible_ids = set(eu["ids"])
    counts = students["counts"]
    country_map = countries["countries"]

    professors = []
    for pid in sorted(eligible_ids):
        eligible_departments = sorted(
            d for d in counts if counts[d] > 10 and d in _professor_departments(raw, pid)
        )
        if eligible_departments:
            professors.append({
                "id": pid,
                "countries": country_map.get(pid, []),
                "eligible_departments": eligible_departments,
            })

    return {"name": contract["name"], "result": {"professors": professors}}


def _professor_departments(raw, pid):
    for p in raw["professors"]:
        if p["id"] == pid:
            return set(p["departments"])
    return set()
