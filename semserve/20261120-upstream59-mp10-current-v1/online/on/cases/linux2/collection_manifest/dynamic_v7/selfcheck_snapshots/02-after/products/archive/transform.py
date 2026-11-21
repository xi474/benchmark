import hashlib
import math


def _check_finite(obj):
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_finite(v)


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    for p in payloads:
        _check_finite(p)
    inventory = _unwrap(payloads[0])
    selection = _unwrap(payloads[1])
    if not isinstance(inventory, dict) or not isinstance(selection, dict):
        raise ValueError("inputs must be objects")

    files = inventory.get("files")
    if not isinstance(files, list):
        raise ValueError("inventory files missing")
    hex_by_path = {}
    for f in files:
        hex_by_path[f["path"]] = f["hex"]

    selected = selection.get("selected")
    if not isinstance(selected, list):
        raise ValueError("selection missing")
    if len(set(selected)) != len(selected):
        raise ValueError("duplicate selected path")

    entries = []
    total = 0
    for p in selected:
        if p not in hex_by_path:
            raise ValueError("selected path not in inventory")
        raw = bytes.fromhex(hex_by_path[p])
        size = len(raw)
        sha = hashlib.sha256(raw).hexdigest()
        entries.append({"path": p, "size": size, "sha256": sha})
        total += size

    return {"name": contract["name"], "result": {"entries": entries, "total_bytes": total}}
