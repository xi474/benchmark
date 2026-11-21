from pathlib import PurePosixPath


def _safe_relative(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    if value == "" or value.startswith("/") or "\\" in value or ":" in value:
        raise ValueError(f"{field} is not a safe relative path: {value!r}")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"{field} is not a safe relative path: {value!r}")
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("input must be an object")

    files = data.get("files")
    download_prefix = data.get("download_prefix")
    archive_prefix = data.get("archive_prefix")
    extensions = data.get("extensions")

    if not isinstance(files, list):
        raise ValueError("files must be a list")
    if not isinstance(download_prefix, str) or not download_prefix.strip():
        raise ValueError("download_prefix must be a non-empty string")
    if not isinstance(archive_prefix, str) or not archive_prefix.strip():
        raise ValueError("archive_prefix must be a non-empty string")
    if not isinstance(extensions, dict):
        raise ValueError("extensions must be an object")

    _safe_relative(download_prefix, "download_prefix")
    _safe_relative(archive_prefix, "archive_prefix")

    # normalize extension keys (case-insensitive) to subdirectory names
    ext_map = {}
    for ext, subdir in extensions.items():
        if not isinstance(ext, str) or not ext.startswith("."):
            raise ValueError("extension keys must be strings starting with '.'")
        if not isinstance(subdir, str) or not subdir.strip():
            raise ValueError("extension values must be non-empty strings")
        _safe_relative(subdir, "extension subdirectory")
        key = ext.casefold()
        if key in ext_map:
            raise ValueError(f"duplicate extension: {ext!r}")
        ext_map[key] = subdir

    moves = []
    seen_targets = set()
    for f in files:
        if not isinstance(f, dict) or "path" not in f:
            raise ValueError("each file must be an object with 'path'")
        path = f["path"]
        if not isinstance(path, str):
            raise ValueError("file path must be a string")
        _safe_relative(path, "file path")
        pp = PurePosixPath(path)
        if len(pp.parts) != 2 or pp.parts[0] != download_prefix:
            # not a direct child of download_prefix -> keep
            continue
        suffix = pp.suffix
        if suffix == "":
            continue
        key = suffix.casefold()
        if key not in ext_map:
            continue
        subdir = ext_map[key]
        target = f"{archive_prefix}/{subdir}/{pp.name}"
        if target in seen_targets:
            raise ValueError(f"target already exists: {target}")
        seen_targets.add(target)
        moves.append({"from": path, "to": target})

    moves.sort(key=lambda m: m["from"])
    return {"name": contract["name"], "result": {"moves": moves}}
