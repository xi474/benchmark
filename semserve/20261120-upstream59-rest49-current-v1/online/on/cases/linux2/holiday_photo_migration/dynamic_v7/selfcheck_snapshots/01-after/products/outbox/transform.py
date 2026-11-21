def transform(payloads, contract):
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
