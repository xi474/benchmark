def _unescape(value):
    return value.replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")


def _parse_options(options):
    parts = [p for p in options.split(",") if p != ""]
    seen = set()
    result = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return sorted(result)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]

    if not isinstance(payload, dict) or "aix" not in payload:
        raise ValueError("missing aix input")
    text = payload["aix"]
    if not isinstance(text, str):
        raise ValueError("aix must be string")

    records = []
    current = None  # dict with mount, dev, vfs, options

    def flush():
        nonlocal current
        if current is None:
            return
        if "dev" not in current:
            raise ValueError("missing device")
        records.append({
            "device": current["dev"],
            "mount": current["mount"],
            "fstype": current.get("vfs", "jfs2"),
            "options": _parse_options(current.get("options", "rw")),
        })
        current = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.endswith(":"):
            # section header (mount point)
            flush()
            mount = line[:-1].strip()
            if mount == "":
                raise ValueError("empty mount point")
            current = {"mount": mount}
            continue
        if "=" not in line:
            raise ValueError("invalid line")
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if current is None:
            raise ValueError("attribute without section header")
        if key not in ("dev", "vfs", "options"):
            raise ValueError("unknown key")
        if key in current:
            raise ValueError("duplicate key")
        current[key] = value

    flush()

    return {"name": contract["name"], "result": {"records": records}}
