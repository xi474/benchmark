import math


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, list):
        for item in obj:
            _reject_non_finite(item)
    elif isinstance(obj, dict):
        for value in obj.values():
            _reject_non_finite(value)


def _is_safe_relpath(value):
    if not isinstance(value, str):
        return False
    if value == "":
        return False
    if value.startswith("/") or "\\" in value or ":" in value:
        return False
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    return True


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        data = payload["result"]
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    _reject_non_finite(data)

    files = data.get("files")
    cleanup_prefix = data.get("cleanup_prefix")

    if not isinstance(files, list):
        raise ValueError("files must be a list")
    if not isinstance(cleanup_prefix, str) or cleanup_prefix == "":
        raise ValueError("cleanup_prefix must be a non-empty string")
    if cleanup_prefix.endswith("/"):
        raise ValueError("cleanup_prefix must not end with slash")
    if not _is_safe_relpath(cleanup_prefix):
        raise ValueError("cleanup_prefix must be a safe relative path")

    prefix_parts = cleanup_prefix.split("/")

    delete = []
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("file entry must be an object")
        path = entry.get("path")
        if not isinstance(path, str) or not _is_safe_relpath(path):
            raise ValueError("file path must be a safe relative path")
        parts = path.split("/")
        if len(parts) <= len(prefix_parts):
            continue
        if parts[:len(prefix_parts)] != prefix_parts:
            continue
        if not parts[-1].endswith(".tmp"):
            continue
        delete.append(path)

    delete.sort()

    return {"name": contract["name"], "result": {"delete": delete}}
