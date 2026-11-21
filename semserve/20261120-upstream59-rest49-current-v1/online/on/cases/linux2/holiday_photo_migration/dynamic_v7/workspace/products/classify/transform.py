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


def _require_str(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be str")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _require_safe_rel(value, field):
    _require_str(value, field)
    if value.startswith("/") or "\\" in value or ":" in value:
        raise ValueError(f"{field} invalid path")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"{field} invalid path")
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be list")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("payload must be object")

    _reject_nonfinite(data)

    files = data["files"]
    photos = data["photos"]
    festivals = data["festivals"]
    destination = data["destination"]
    recipient = data["recipient"]

    # validate festivals
    if not isinstance(festivals, list):
        raise ValueError("festivals must be list")
    seen_festivals = set()
    for f in festivals:
        _require_str(f, "festival")
        if f in seen_festivals:
            raise ValueError("duplicate festival")
        seen_festivals.add(f)

    _require_safe_rel(destination, "destination")
    _require_str(recipient, "recipient")

    # validate files
    if not isinstance(files, list):
        raise ValueError("files must be list")
    file_paths = set()
    for f in files:
        if not isinstance(f, dict):
            raise ValueError("file entry must be object")
        p = _require_str(f.get("path"), "file.path")
        if p in file_paths:
            raise ValueError("duplicate file path")
        file_paths.add(p)
        h = f.get("hex")
        if not isinstance(h, str):
            raise ValueError("file.hex must be str")
        try:
            bytes.fromhex(h)
        except ValueError:
            raise ValueError("invalid hex")

    # validate photos
    if not isinstance(photos, list):
        raise ValueError("photos must be list")
    seen_photo_paths = set()
    for ph in photos:
        if not isinstance(ph, dict):
            raise ValueError("photo entry must be object")
        p = _require_str(ph.get("path"), "photo.path")
        if p in seen_photo_paths:
            raise ValueError("duplicate photo path")
        seen_photo_paths.add(p)
        if p not in file_paths:
            raise ValueError("photo path not in files")
        _require_str(ph.get("festival"), "photo.festival")

    festival_set = set(festivals)
    selected = []
    for ph in photos:
        if ph["festival"] in festival_set:
            selected.append({"path": ph["path"], "festival": ph["festival"]})
    selected.sort(key=lambda x: (x["festival"], x["path"]))

    selected_festivals = {s["festival"] for s in selected}
    missing = sorted(f for f in festivals if f not in selected_festivals)

    return {
        "name": contract["name"],
        "result": {"selected": selected, "missing": missing},
    }
