import copy
import math


def _is_finite_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return math.isfinite(v)
    return False


def _is_nonneg_number(v):
    return _is_finite_number(v) and v >= 0


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("input must be object")

    # Unwrap name/result envelope if present.
    if set(payload.keys()) == {"name", "result"}:
        data = payload["result"]
    else:
        data = payload
    if not isinstance(data, dict):
        raise ValueError("business input must be object")

    classes = data.get("classes")
    sample_weight = data.get("sample_weight")
    members = data.get("members")

    if not isinstance(classes, list) or not classes:
        raise ValueError("classes required non-empty list")
    seen = set()
    for c in classes:
        if not isinstance(c, str) or not c.strip():
            raise ValueError("class must be non-empty string")
        if c in seen:
            raise ValueError("duplicate class")
        seen.add(c)

    if not isinstance(sample_weight, list):
        raise ValueError("sample_weight must be list")
    for w in sample_weight:
        if not _is_nonneg_number(w):
            raise ValueError("sample_weight must be non-negative number")
    sample_count = len(sample_weight)

    if not isinstance(members, list):
        raise ValueError("members must be list")

    ids = set()
    active_members = []
    for m in members:
        if not isinstance(m, dict):
            raise ValueError("member must be object")
        if "id" not in m or "active" not in m:
            raise ValueError("member missing id/active")
        mid = m["id"]
        if not isinstance(mid, str) or not mid.strip():
            raise ValueError("member id must be non-empty string")
        if mid in ids:
            raise ValueError("duplicate member id")
        ids.add(mid)
        if not isinstance(m["active"], bool):
            raise ValueError("active must be bool")
        if not m["active"]:
            continue
        active_members.append(m)

    if not active_members:
        raise ValueError("at least one active member required")

    total_weight = 0.0
    for m in active_members:
        w = m.get("weight")
        if not _is_nonneg_number(w):
            raise ValueError("member weight must be non-negative number")
        total_weight += w
    if total_weight <= 0:
        raise ValueError("active member weight sum must be > 0")

    for m in active_members:
        preds = m.get("predictions")
        mclasses = m.get("classes")
        probs = m.get("probabilities")
        if not isinstance(preds, list) or len(preds) != sample_count:
            raise ValueError("predictions length must equal sample count")
        for p in preds:
            if p not in classes:
                raise ValueError("prediction label not in global classes")
        if not isinstance(mclasses, list) or sorted(mclasses) != sorted(classes):
            raise ValueError("member classes must be permutation of global classes")
        if not isinstance(probs, list) or len(probs) != sample_count:
            raise ValueError("probabilities rows must equal sample count")
        for row in probs:
            if not isinstance(row, list) or len(row) != len(mclasses):
                raise ValueError("probability row length mismatch")
            s = 0.0
            for v in row:
                if not _is_nonneg_number(v):
                    raise ValueError("probability must be non-negative number")
                s += v
            if abs(s - 1.0) > 1e-9:
                raise ValueError("probability row must sum to 1")

    result_members = []
    for m in active_members:
        nm = copy.deepcopy(m)
        nm["fit_weight"] = copy.deepcopy(sample_weight)
        result_members.append(nm)

    return {
        "name": contract["name"],
        "result": {
            "classes": copy.deepcopy(classes),
            "sample_count": sample_count,
            "members": result_members,
        },
    }
