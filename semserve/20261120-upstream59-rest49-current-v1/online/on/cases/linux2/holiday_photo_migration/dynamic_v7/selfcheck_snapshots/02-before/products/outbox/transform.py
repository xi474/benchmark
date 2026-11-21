import math


def _reject_nonfinite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
        return
    if isinstance(obj, list):
        for item in obj:
            _reject_nonfinite(item)
        return
    if isinstance(obj, dict):
        for value in obj.values():
            _reject_nonfinite(value)
        return


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be list")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    snapshot = payloads[0]
    classification = payloads[1]
    migration = payloads[2]

    # Unwrap name/result envelope if present.
    def unwrap(obj):
        if isinstance(obj, dict) and set(obj) == {"name", "result"}:
            return obj["result"]
        return obj

    snapshot = unwrap(snapshot)
    classification = unwrap(classification)
    migration = unwrap(migration)

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be object")
    if not isinstance(classification, dict):
        raise ValueError("classification must be object")
    if not isinstance(migration, dict):
        raise ValueError("migration must be object")

    _reject_nonfinite(snapshot)
    _reject_nonfinite(classification)
    _reject_nonfinite(migration)

    recipient = snapshot["recipient"]
    missing = classification["missing"]
    moves = migration["moves"]

    attachments = sorted(m["to"] for m in moves)

    if missing:
        message = "Missing: " + ", ".join(missing)
    else:
        message = "Photos ready"

    result = {
        "to": recipient,
        "attachments": attachments,
        "missing": missing,
        "message": message,
    }

    return {"name": contract["name"], "result": result}
