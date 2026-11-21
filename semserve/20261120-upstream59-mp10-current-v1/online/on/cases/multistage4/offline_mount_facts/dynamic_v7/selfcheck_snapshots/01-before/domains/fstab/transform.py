def _unescape(s):
    return s.replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")


def _parse_fstab(text):
    records = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split()
        if not (4 <= len(cols) <= 6):
            raise ValueError("fstab line must have 4 to 6 columns")
        device = _unescape(cols[0])
        mount = _unescape(cols[1])
        fstype = _unescape(cols[2])
        options = _unescape(cols[3])
        opts = []
        for o in options.split(","):
            o = o.strip()
            if o and o not in opts:
                opts.append(o)
        opts.sort()
        records.append({
            "device": device,
            "mount": mount,
            "fstype": fstype,
            "options": opts,
        })
    return records


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict) or "fstab" not in payload:
        raise ValueError("missing fstab")
    text = payload["fstab"]
    if not isinstance(text, str):
        raise ValueError("fstab must be string")
    records = _parse_fstab(text)
    return {"name": contract["name"], "result": {"records": records}}
