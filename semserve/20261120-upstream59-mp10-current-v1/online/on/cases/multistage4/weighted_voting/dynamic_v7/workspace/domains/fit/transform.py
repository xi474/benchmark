import copy
import math


def _is_bool(v):
    return isinstance(v, bool)


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_finite_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return math.isfinite(v)
    return False


def _require(cond, msg="invalid input"):
    if not cond:
        raise ValueError(msg)


def transform(payloads, contract):
    _require(len(payloads) == len(contract["inputs"]), "payload count mismatch")
    raw = payloads[0]
    # If the object has exactly keys name/result, only result is business input.
    if isinstance(raw, dict) and set(raw.keys()) == {"name", "result"}:
        data = raw["result"]
    else:
        data = raw

    _require(isinstance(data, dict), "input must be object")

    classes = data.get("classes")
    sample_weight = data.get("sample_weight")
    members = data.get("members")

    _require(isinstance(classes, list), "classes must be list")
    _require(len(classes) > 0, "classes must be non-empty")
    seen = set()
    for c in classes:
        _require(isinstance(c, str), "class must be string")
        _require(c.strip() != "", "class must be non-empty")
        _require(c not in seen, "duplicate class")
        seen.add(c)

    _require(isinstance(sample_weight, list), "sample_weight must be list")
    n_samples = len(sample_weight)
    for w in sample_weight:
        _require(_is_finite_number(w) and w >= 0, "sample_weight must be non-negative finite")

    _require(isinstance(members, list), "members must be list")
    _require(len(members) > 0, "members must be non-empty")

    member_ids = set()
    active_members = []
    for m in members:
        _require(isinstance(m, dict), "member must be object")
        mid = m.get("id")
        _require(isinstance(mid, str) and mid.strip() != "", "member id must be non-empty string")
        _require(mid not in member_ids, "duplicate member id")
        member_ids.add(mid)

        active = m.get("active")
        _require(_is_bool(active), "active must be bool")

        if not active:
            # closed member: only id/active validated
            continue

        weight = m.get("weight")
        _require(_is_finite_number(weight) and weight >= 0, "member weight must be non-negative finite")

        predictions = m.get("predictions")
        _require(isinstance(predictions, list), "predictions must be list")
        _require(len(predictions) == n_samples, "predictions length must equal sample count")
        for p in predictions:
            _require(isinstance(p, str) and p in seen, "prediction label must be a global class")

        mclasses = m.get("classes")
        _require(isinstance(mclasses, list), "member classes must be list")
        _require(sorted(mclasses) == sorted(classes), "member classes must be a permutation of global classes")

        probabilities = m.get("probabilities")
        _require(isinstance(probabilities, list), "probabilities must be list")
        _require(len(probabilities) == n_samples, "probabilities rows must equal sample count")
        for row in probabilities:
            _require(isinstance(row, list), "probability row must be list")
            _require(len(row) == len(mclasses), "probability row width mismatch")
            total = 0.0
            for v in row:
                _require(_is_finite_number(v) and v >= 0, "probability must be non-negative finite")
                total += v
            _require(abs(total - 1.0) <= 1e-9, "probability row must sum to 1")

        active_members.append(m)

    _require(len(active_members) > 0, "at least one active member required")
    total_weight = sum(m["weight"] for m in active_members)
    _require(total_weight > 0, "active member weight sum must be positive")

    out_members = []
    for m in active_members:
        cm = copy.deepcopy(m)
        cm["fit_weight"] = list(sample_weight)
        out_members.append(cm)

    return {
        "name": contract["name"],
        "result": {
            "classes": list(classes),
            "sample_count": n_samples,
            "members": out_members,
        },
    }
