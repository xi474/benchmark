def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def _records(payload):
    data = _unwrap(payload)
    if not isinstance(data, dict) or "records" not in data:
        raise ValueError("missing records")
    records = data["records"]
    if not isinstance(records, list):
        raise ValueError("records must be list")
    return records


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    sources = ["fstab", "aix", "mount"]
    by_mount = {}
    for source, payload in zip(sources, payloads):
        for rec in _records(payload):
            if not isinstance(rec, dict):
                raise ValueError("record must be object")
            mount = rec.get("mount")
            if mount is None:
                raise ValueError("record missing mount")
            entry = dict(rec)
            entry["source"] = source
            by_mount.setdefault(mount, []).append(entry)

    records = []
    conflicts = []
    for mount in sorted(by_mount):
        evidence = by_mount[mount]
        winner = evidence[0]
        records.append(winner)
        # conflict if any record differs in device/fstype/options
        base = (winner.get("device"), winner.get("fstype"), winner.get("options"))
        conflict = False
        for rec in evidence[1:]:
            cur = (rec.get("device"), rec.get("fstype"), rec.get("options"))
            if cur != base:
                conflict = True
                break
        if conflict:
            conflicts.append({"mount": mount, "evidence": evidence})

    return {"name": contract["name"], "result": {"records": records, "conflicts": conflicts}}
