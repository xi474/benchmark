import math


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    fit = _unwrap(payloads[0])
    if not isinstance(fit, dict):
        raise ValueError("fit result must be an object")

    classes = fit.get("classes")
    if not isinstance(classes, list) or not classes:
        raise ValueError("classes required")
    for c in classes:
        if not isinstance(c, str) or not c.strip():
            raise ValueError("invalid class")
    if len(set(classes)) != len(classes):
        raise ValueError("duplicate classes")

    members = fit.get("members")
    if not isinstance(members, list):
        raise ValueError("members required")

    sample_count = fit.get("sample_count")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("sample_count required")

    class_index = {c: i for i, c in enumerate(classes)}
    n = len(classes)

    predictions = []
    probabilities = []

    for s in range(sample_count):
        totals = [0.0] * n
        weight_sum = 0.0
        for m in members:
            if not isinstance(m, dict):
                raise ValueError("member must be object")
            fw = m.get("fit_weight")
            if not isinstance(fw, list):
                raise ValueError("fit_weight required")
            if len(fw) != sample_count:
                raise ValueError("fit_weight length mismatch")
            w = fw[s]
            if isinstance(w, bool) or not isinstance(w, (int, float)):
                raise ValueError("fit_weight required")
            if isinstance(w, float) and not math.isfinite(w):
                raise ValueError("non-finite weight")
            if w < 0:
                raise ValueError("negative weight")

            mclasses = m.get("classes")
            probs = m.get("probabilities")
            if not isinstance(mclasses, list) or not isinstance(probs, list):
                raise ValueError("member classes/probabilities required")
            if len(mclasses) != n:
                raise ValueError("member classes must be permutation of global classes")
            if sorted(mclasses) != sorted(classes):
                raise ValueError("member classes must be permutation of global classes")
            if len(probs) != sample_count:
                raise ValueError("probabilities length mismatch")

            row = probs[s]
            if not isinstance(row, list) or len(row) != n:
                raise ValueError("probability row length mismatch")

            for j, c in enumerate(mclasses):
                if c not in class_index:
                    raise ValueError("unknown class")
                p = row[j]
                if isinstance(p, bool) or not isinstance(p, (int, float)):
                    raise ValueError("invalid probability")
                if isinstance(p, float) and not math.isfinite(p):
                    raise ValueError("non-finite probability")
                if p < 0:
                    raise ValueError("negative probability")
                totals[class_index[c]] += w * p
            weight_sum += w

        if weight_sum <= 0:
            raise ValueError("weight sum must be positive")

        avg = [t / weight_sum for t in totals]
        probabilities.append(avg)

        best = max(avg)
        pred = None
        for i, v in enumerate(avg):
            if abs(v - best) <= 1e-9:
                pred = classes[i]
                break
        predictions.append(pred)

    return {"name": contract["name"], "result": {"predictions": predictions, "probabilities": probabilities}}
