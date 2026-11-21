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

    # Unwrap name/result envelope if present.
    if isinstance(snapshot, dict) and set(snapshot) == {"name", "result"}:
        snapshot = snapshot["result"]
    if isinstance(classification, dict) and set(classification) == {"name", "result"}:
        classification = classification["result"]

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be object")
    if not isinstance(classification, dict):
        raise ValueError("classification must be object")

    _reject_nonfinite(snapshot)
    _reject_nonfinite(classification)

    destination = snapshot["destination"]
    files = snapshot["files"]
    selected = classification["selected"]

    file_by_path = {}
    for f in files:
        file_by_path[f["path"]] = f

    moves = []
    for item in selected:
        src = item["path"]
        festival = item["festival"]
        dst = destination + "/" + src
        if dst in file_by_path:
            raise ValueError("destination already exists")
        moves.append({"from": src, "to": dst, "festival": festival})

    moves.sort(key=lambda m: (m["from"], m["to"]))

    # Build resulting files: unselected files unchanged, selected files moved.
    selected_paths = {m["from"] for m in moves}
    result_files = []
    for f in files:
        if f["path"] in selected_paths:
            continue
        result_files.append({"path": f["path"], "hex": f["hex"]})
    for m in moves:
        result_files.append({"path": m["to"], "hex": file_by_path[m["from"]]["hex"]})
    result_files.sort(key=lambda f: f["path"])

    return {"name": contract["name"], "result": {"moves": moves, "files": result_files}}
