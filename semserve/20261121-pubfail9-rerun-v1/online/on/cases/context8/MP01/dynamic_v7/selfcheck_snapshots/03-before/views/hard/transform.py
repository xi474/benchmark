def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        data = payload["result"]
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("fit result must be an object")

    classes = data["classes"]
    members = data["members"]

    if not isinstance(classes, list) or not classes:
        raise ValueError("classes must be a non-empty list")
    if not isinstance(members, list):
        raise ValueError("members must be a list")

    sample_count = None
    for m in members:
        preds = m["predictions"]
        if sample_count is None:
            sample_count = len(preds)
        elif len(preds) != sample_count:
            raise ValueError("inconsistent sample count")

    if sample_count is None:
        sample_count = 0

    n_classes = len(classes)
    class_index = {c: i for i, c in enumerate(classes)}

    scores = [[0.0] * n_classes for _ in range(sample_count)]

    for m in members:
        fit_weight = m["fit_weight"]
        preds = m["predictions"]
        for s in range(sample_count):
            label = preds[s]
            if label not in class_index:
                raise ValueError("label not in global classes")
            scores[s][class_index[label]] += fit_weight[s]

    predictions = []
    for s in range(sample_count):
        row = scores[s]
        best = max(row)
        idx = row.index(best)
        predictions.append(classes[idx])

    return {"name": contract["name"], "result": {"predictions": predictions, "scores": scores}}
