import hashlib


def _require_str(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _safe_rel_path(value, field):
    _require_str(value, field)
    if value == "" or value != value.strip():
        raise ValueError(f"{field} must be non-empty after strip")
    if value.startswith("/") or "\\" in value or ":" in value:
        raise ValueError(f"{field} is not a safe relative path")
    parts = value.split("/")
    if any(seg in ("", ".", "..") for seg in parts):
        raise ValueError(f"{field} is not a safe relative path")
    return value


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError("input must be an object")

    files = data.get("files")
    attachments = data.get("attachments")
    recipients = data.get("recipients")
    send_ok = data.get("send_ok")

    if not isinstance(files, list):
        raise ValueError("files must be a list")
    if not isinstance(attachments, list):
        raise ValueError("attachments must be a list")
    if not isinstance(recipients, list):
        raise ValueError("recipients must be a list")
    if not isinstance(send_ok, dict):
        raise ValueError("send_ok must be an object")

    # Build file map: path -> hex
    file_map = {}
    for f in files:
        if not isinstance(f, dict):
            raise ValueError("file entry must be an object")
        path = _safe_rel_path(f.get("path"), "path")
        hexv = f.get("hex")
        if not isinstance(hexv, str):
            raise ValueError("hex must be a string")
        if path in file_map:
            raise ValueError("duplicate file path")
        file_map[path] = hexv

    # Attachments: dedupe, sort, must exist
    att_paths = []
    for a in attachments:
        p = _safe_rel_path(a, "attachment")
        if p not in file_map:
            raise ValueError("attachment not in files")
        att_paths.append(p)
    att_paths = sorted(set(att_paths))

    # Recipients: unique non-empty ids
    recips = []
    for r in recipients:
        if not isinstance(r, str) or r.strip() == "":
            raise ValueError("recipient must be non-empty string")
        if r in recips:
            raise ValueError("duplicate recipient")
        recips.append(r)
    recips = sorted(recips)

    attachments_out = []
    for p in att_paths:
        raw = bytes.fromhex(file_map[p])
        attachments_out.append({"path": p, "sha256": hashlib.sha256(raw).hexdigest()})

    receipts = []
    for r in recips:
        if r not in send_ok:
            raise ValueError("recipient missing from send_ok")
        ok = send_ok[r]
        if not isinstance(ok, bool):
            raise ValueError("send_ok value must be bool")
        receipts.append({"recipient": r, "ok": ok})

    return {"name": contract["name"], "result": {"attachments": attachments_out, "receipts": receipts}}
