def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    hard = payloads[0]
    soft = payloads[1]

    if isinstance(hard, dict) and set(hard.keys()) == {"name", "result"}:
        hard = hard["result"]
    if isinstance(soft, dict) and set(soft.keys()) == {"name", "result"}:
        soft = soft["result"]

    if not isinstance(hard, dict) or not isinstance(soft, dict):
        raise ValueError("inputs must be objects")

    hard_preds = hard.get("predictions")
    soft_preds = soft.get("predictions")
    if not isinstance(hard_preds, list) or not isinstance(soft_preds, list):
        raise ValueError("predictions must be lists")

    if len(hard_preds) != len(soft_preds):
        raise ValueError("sample counts differ")

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
