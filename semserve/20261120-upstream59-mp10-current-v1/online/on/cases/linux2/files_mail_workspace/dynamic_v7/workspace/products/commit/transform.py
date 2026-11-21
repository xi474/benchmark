import math


def _reject_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number not allowed")
    if isinstance(value, dict):
        for v in value.values():
            _reject_nonfinite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_nonfinite(v)
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    snapshot, files_result, mail_result, reply_result = payloads

    def unwrap(obj):
        if isinstance(obj, dict) and set(obj) == {"name", "result"}:
            return obj["result"]
        return obj

    snapshot = unwrap(snapshot)
    files_result = unwrap(files_result)
    mail_result = unwrap(mail_result)
    reply_result = unwrap(reply_result)

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if not isinstance(files_result, dict):
        raise ValueError("files result must be an object")
    if not isinstance(mail_result, dict):
        raise ValueError("mail result must be an object")
    if not isinstance(reply_result, dict):
        raise ValueError("reply result must be an object")

    _reject_nonfinite(snapshot)
    _reject_nonfinite(files_result)
    _reject_nonfinite(mail_result)
    _reject_nonfinite(reply_result)

    moves = files_result.get("moves")
    trash_ids = mail_result.get("trash_ids")
    if not isinstance(moves, list):
        raise ValueError("moves must be a list")
    if not isinstance(trash_ids, list):
        raise ValueError("trash_ids must be a list")

    reply_email_id = reply_result.get("email_id")
    if reply_email_id in trash_ids:
        raise ValueError("reply target is also in trash_ids")

    files = snapshot.get("files")
    emails = snapshot.get("emails")
    if not isinstance(files, list):
        raise ValueError("files must be a list")
    if not isinstance(emails, list):
        raise ValueError("emails must be a list")

    path_map = {}
    for f in files:
        if not isinstance(f, dict) or "path" not in f:
            raise ValueError("each file must be an object with 'path'")
        path_map[f["path"]] = f

    for m in moves:
        src = m["from"]
        dst = m["to"]
        if src not in path_map:
            raise ValueError("move source not found: " + str(src))
        if dst in path_map:
            raise ValueError("move target already exists: " + str(dst))
        f = path_map.pop(src)
        new_f = dict(f)
        new_f["path"] = dst
        path_map[dst] = new_f

    out_files = []
    for path in sorted(path_map):
        out_files.append(path_map[path])

    trash_set = set(trash_ids)
    out_emails = []
    for e in emails:
        if not isinstance(e, dict):
            raise ValueError("each email must be an object")
        new_e = dict(e)
        if e.get("id") in trash_set:
            new_e["folder"] = "TRASH"
        out_emails.append(new_e)
    out_emails.sort(key=lambda e: e.get("id"))

    return {
        "name": contract["name"],
        "result": {
            "files": out_files,
            "emails": out_emails,
            "reply": reply_result,
        },
    }
