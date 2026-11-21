def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    hard = _unwrap(payloads[0])
    soft = _unwrap(payloads[1])

    if not isinstance(hard, dict) or not isinstance(soft, dict):
        raise ValueError("inputs must be objects")

    hard_preds = hard.get("predictions")
    soft_preds = soft.get("predictions")

    if not isinstance(hard_preds, list) or not isinstance(soft_preds, list):
        raise ValueError("predictions must be lists")

    if len(hard_preds) != len(soft_preds):
        raise ValueError("sample count mismatch")

    disagreements = [
        i for i in range(len(hard_preds)) if hard_preds[i] != soft_preds[i]
    ]

    return {
        "name": contract["name"],
        "result": {
            "hard": hard_preds,
            "soft": soft_preds,
            "disagreements": disagreements,
        },
    }
