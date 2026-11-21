import json
from datetime import datetime


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    jsonl_text = payload.get("jsonl_text")
    if not isinstance(jsonl_text, str):
        raise ValueError("jsonl_text must be a string")

    records = {}
    for raw_line in jsonl_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line, parse_constant=_reject_constant)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("bad JSONL line") from exc
        if not isinstance(obj, dict):
            raise ValueError("JSONL line must be an object")
        _merge_record(records, obj)

    result = {
        "records": sorted(
            (r for r in records.values()),
            key=lambda r: r["id"],
        )
    }
    return {"name": contract["name"], "result": result}


def _reject_constant(value):
    raise ValueError("non-finite number not allowed")


def _merge_record(records, obj):
    user_id = _resolve_id(obj)
    if user_id is None:
        return
    rec = records.get(user_id)
    if rec is None:
        rec = {"id": user_id}
        records[user_id] = rec

    # name / full_name
    name = _pick(obj, "name", "full_name")
    if name is not None:
        rec["name"] = name

    # email / mail
    email = _pick(obj, "email", "mail")
    if email is not None:
        rec["email"] = email

    # joined / joined_at
    joined = _pick(obj, "joined", "joined_at")
    if joined is not None:
        rec["joined"] = _normalize_date(joined)


def _resolve_id(obj):
    if "id" not in obj:
        return None
    raw = obj["id"]
    if isinstance(raw, bool):
        raise ValueError("id must not be bool")
    if isinstance(raw, int):
        return str(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise ValueError("id must be non-empty")
        return s
    raise ValueError("id must be str or int")


def _pick(obj, *keys):
    for k in keys:
        if k in obj and obj[k] is not None:
            return obj[k]
    return None


def _normalize_date(value):
    if not isinstance(value, str):
        raise ValueError("joined must be a string")
    if not value.strip():
        raise ValueError("joined must be non-empty")
    v = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("invalid joined date")
