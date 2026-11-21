import copy


def _safe_rel_path(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if value != value.strip() or value == "":
        raise ValueError(f"{field} must be non-empty after strip")
    if value.startswith("/") or "\\" in value or ":" in value:
        raise ValueError(f"{field} is not a safe relative path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"{field} is not a safe relative path")
    return value


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    if not isinstance(contract, dict):
        raise ValueError("contract must be a dict")
    if len(payloads) != len(contract.get("inputs", [])):
        raise ValueError("payload count mismatch")

    snapshot = _unwrap(payloads[0])
    receipts = _unwrap(payloads[1])
    cleanup = _unwrap(payloads[2])

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if not isinstance(receipts, dict):
        raise ValueError("receipts must be an object")
    if not isinstance(cleanup, dict):
        raise ValueError("cleanup must be an object")

    archive_prefix = _safe_rel_path(snapshot["archive_prefix"], "archive_prefix")

    files = snapshot["files"]
    if not isinstance(files, list):
        raise ValueError("files must be a list")
    file_map = {}
    for f in files:
        if not isinstance(f, dict):
            raise ValueError("file entry must be an object")
        path = _safe_rel_path(f["path"], "path")
        if path in file_map:
            raise ValueError("duplicate file path")
        hexv = f["hex"]
        if not isinstance(hexv, str):
            raise ValueError("hex must be a string")
        file_map[path] = hexv

    attachments = snapshot["attachments"]
    if not isinstance(attachments, list):
        raise ValueError("attachments must be a list")
    seen = set()
    for a in attachments:
        p = _safe_rel_path(a, "attachment")
        if p in seen:
            raise ValueError("duplicate attachment")
        seen.add(p)
        if p not in file_map:
            raise ValueError("attachment not in files")

    # receipts
    rec_list = receipts.get("receipts")
    if not isinstance(rec_list, list):
        raise ValueError("receipts must be a list")
    all_ok = True
    for r in rec_list:
        if not isinstance(r, dict):
            raise ValueError("receipt entry must be an object")
        if r.get("ok") is not True:
            all_ok = False

    # cleanup delete list
    deleted = cleanup.get("delete")
    if not isinstance(deleted, list):
        raise ValueError("cleanup delete must be a list")
    deleted = sorted(deleted)

    moves = []
    blocked = False
    if all_ok and len(rec_list) > 0:
        targets = {}
        for a in attachments:
            to = archive_prefix + "/" + a
            if to in targets:
                raise ValueError("duplicate target")
            targets[to] = a
        # check target existence
        for to in targets:
            if to in file_map:
                raise ValueError("target already exists")
        # cleanup must not overlap move source
        for d in deleted:
            if d in seen:
                raise ValueError("cleanup overlaps move source")
        for a in attachments:
            moves.append({"from": a, "to": archive_prefix + "/" + a})
    else:
        blocked = True

    moves.sort(key=lambda m: m["from"])

    out_files = [{"path": p, "hex": file_map[p]} for p in sorted(file_map)]

    return {
        "name": contract["name"],
        "result": {
            "moves": moves,
            "deleted": deleted,
            "blocked": blocked,
            "files": out_files,
        },
    }
