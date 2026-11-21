import re


def _unescape(text):
    return text.replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\")


def _parse_line(line):
    # Fixed Linux syntax: device on mountpoint type fstype (option1,option2)
    m = re.match(r"^(\S+) on (\S+) type (\S+) \((.*)\)$", line)
    if m is None:
        raise ValueError("invalid mount line")
    device = _unescape(m.group(1))
    mount = _unescape(m.group(2))
    fstype = m.group(3)
    options_raw = m.group(4)
    if options_raw == "":
        raise ValueError("empty options")
    options = [o for o in options_raw.split(",")]
    options = sorted(set(options))
    return {"device": device, "mount": mount, "fstype": fstype, "options": options}


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict) or "mount" not in payload:
        raise ValueError("missing mount input")
    text = payload["mount"]
    if not isinstance(text, str):
        raise ValueError("mount must be string")
    records = []
    for raw in text.splitlines():
        line = raw.strip()
        if line == "":
            continue
        records.append(_parse_line(line))
    return {"name": contract["name"], "result": {"records": records}}
