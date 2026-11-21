def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = _unwrap(payloads[0])
    if not isinstance(payload, dict):
        raise ValueError("input must be an object")
    pieces = payload.get("pieces")
    if not isinstance(pieces, list):
        raise ValueError("pieces must be a list")
    policy = payload.get("attribute_policy")
    if policy not in ("drop_conflicts", "first"):
        raise ValueError("invalid attribute_policy")

    merged = {}
    seen = {}
    for piece in pieces:
        if not isinstance(piece, dict):
            raise ValueError("piece must be an object")
        attrs = piece.get("attrs")
        if not isinstance(attrs, dict):
            raise ValueError("attrs must be an object")
        for key, value in attrs.items():
            if key not in seen:
                seen[key] = [value]
            else:
                seen[key].append(value)

    conflicts = []
    for key in sorted(seen):
        values = seen[key]
        first = values[0]
        if policy == "first":
            merged[key] = first
        else:  # drop_conflicts
            if all(v == first for v in values):
                merged[key] = first
            else:
                conflicts.append(key)

    return {"name": contract["name"], "result": {"attrs": merged, "conflicts": conflicts}}
