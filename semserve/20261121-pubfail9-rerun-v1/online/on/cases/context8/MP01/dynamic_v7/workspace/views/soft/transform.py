import math


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    if len(payloads) != 1:
        raise ValueError("soft_vote expects exactly one input")

    payload = payloads[0]
    # When the input object has exactly keys name/result, only result is business input.
    if isinstance(payload, dict) and set(payload.keys()) == {"name", "result"}:
        data = payload["result"]
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("input must be an object")

    classes = data.get("classes")
    members = data.get("members")
    if not isinstance(classes, list) or not isinstance(members, list):
        raise ValueError("missing classes or members")

    if len(classes) == 0:
        raise ValueError("classes must be non-empty")
    for c in classes:
        if not isinstance(c, str) or not c.strip():
            raise ValueError("invalid class label")
    if len(set(classes)) != len(classes):
        raise ValueError("duplicate classes")

    n_classes = len(classes)
    class_index = {c: i for i, c in enumerate(classes)}

    sample_count = None
    for m in members:
        if not isinstance(m, dict):
            raise ValueError("member must be object")
        probs = m.get("probabilities")
        mclasses = m.get("classes")
        weight = m.get("weight")
        if not isinstance(probs, list) or not isinstance(mclasses, list):
            raise ValueError("member missing probabilities/classes")
        if not _is_finite_number(weight) or weight < 0:
            raise ValueError("invalid member weight")
        if len(mclasses) != n_classes or set(mclasses) != set(classes):
            raise ValueError("member classes must be a permutation of global classes")
        if sample_count is None:
            sample_count = len(probs)
        elif len(probs) != sample_count:
            raise ValueError("inconsistent sample count")

    if sample_count is None:
        sample_count = 0

    # Accumulate weighted probabilities mapped to global class order.
    totals = [[0.0] * n_classes for _ in range(sample_count)]
    weight_sum = 0.0
    for m in members:
        weight = m["weight"]
        weight_sum += weight
        mclasses = m["classes"]
        probs = m["probabilities"]
        # column order of this member's probabilities follows mclasses
        for s in range(sample_count):
            row = probs[s]
            if not isinstance(row, list) or len(row) != n_classes:
                raise ValueError("probability row size mismatch")
            for col, cls in enumerate(mclasses):
                p = row[col]
                if not _is_finite_number(p) or p < 0:
                    raise ValueError("invalid probability")
                totals[s][class_index[cls]] += weight * p

    if weight_sum <= 0:
        raise ValueError("total weight must be positive")

    probabilities = []
    predictions = []
    for s in range(sample_count):
        row = [totals[s][i] / weight_sum for i in range(n_classes)]
        probabilities.append(row)
        best = max(range(n_classes), key=lambda i: row[i])
        predictions.append(classes[best])

    return {"name": contract["name"], "result": {"predictions": predictions, "probabilities": probabilities}}
