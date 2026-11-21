import copy


def _safe_rel_path(s):
    if not isinstance(s, str):
        raise ValueError("path must be string")
    if s != s.strip() or s == "":
        raise ValueError("path must be non-empty after strip")
    if s.startswith("/") or "\\" in s or ":" in s:
        raise ValueError("unsafe path")
    parts = s.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("unsafe path segment")
    return s


def _valid_hex(s):
    if not isinstance(s, str):
        raise ValueError("hex must be string")
    try:
        bytes.fromhex(s)
    except ValueError:
        raise ValueError("invalid hex")
    return s


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("input must be object")

    files = payload.get("files")
    if files is None:
        raise ValueError("missing files")
    if not isinstance(files, list):
        raise ValueError("files must be list")

    seen = set()
    normal = []
    symlinks = []
    for f in files:
        if not isinstance(f, dict):
            raise ValueError("file entry must be object")
        path = _safe_rel_path(f.get("path"))
        if path in seen:
            raise ValueError("duplicate path")
        seen.add(path)
        kind = f.get("kind")
        if kind not in ("file", "symlink"):
            raise ValueError("invalid kind")
        if kind == "file":
            hexv = _valid_hex(f.get("hex"))
            normal.append({"path": path, "hex": hexv})
        else:
            target = f.get("target")
            if target is None:
                raise ValueError("symlink target required")
            _safe_rel_path(target)
            symlinks.append(path)

    normal.sort(key=lambda x: x["path"])
    symlinks.sort()
    return {"name": contract["name"], "result": {"files": normal, "symlinks": symlinks}}
