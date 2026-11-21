import fnmatch
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
    snapshot = _unwrap(payloads[0])
    inventory = _unwrap(payloads[1])
    if not isinstance(snapshot, dict) or not isinstance(inventory, dict):
        raise ValueError("inputs must be objects")

    manifest = snapshot.get("manifest")
    build_ignore = snapshot.get("build_ignore")
    if manifest is not None and build_ignore is not None:
        raise ValueError("manifest and build_ignore cannot both be set")

    files = inventory.get("files")
    if not isinstance(files, list):
        raise ValueError("inventory files missing")
    normal_paths = [f["path"] for f in files]

    if manifest is None:
        selected = set(normal_paths)
        if build_ignore is not None:
            if not isinstance(build_ignore, list):
                raise ValueError("build_ignore must be list")
            for pat in build_ignore:
                if not isinstance(pat, str):
                    raise ValueError("pattern must be string")
                selected = {p for p in selected if not fnmatch.fnmatchcase(p, pat)}
    else:
        if not isinstance(manifest, str):
            raise ValueError("manifest must be string")
        selected = set()
        for raw in manifest.splitlines():
            line = raw.strip()
            if line == "" or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                raise ValueError("unknown manifest syntax")
            op = parts[0]
            if op == "include":
                if len(parts) != 2:
                    raise ValueError("include takes one pattern")
                pat = parts[1]
                for p in normal_paths:
                    if fnmatch.fnmatchcase(p, pat):
                        selected.add(p)
            elif op == "exclude":
                if len(parts) != 2:
                    raise ValueError("exclude takes one pattern")
                pat = parts[1]
                selected = {p for p in selected if not fnmatch.fnmatchcase(p, pat)}
            elif op == "recursive-include":
                if len(parts) != 3:
                    raise ValueError("recursive-include takes DIR PATTERN")
                d = parts[1]
                pat = parts[2]
                prefix = d.rstrip("/") + "/"
                for p in normal_paths:
                    if p.startswith(prefix):
                        base = p[len(prefix):]
                        if "/" not in base and fnmatch.fnmatchcase(base, pat):
                            selected.add(p)
            elif op == "global-exclude":
                if len(parts) != 2:
                    raise ValueError("global-exclude takes one pattern")
                pat = parts[1]
                selected = {p for p in selected if not fnmatch.fnmatchcase(p.rsplit("/", 1)[-1], pat)}
            else:
                raise ValueError("unknown manifest syntax")

    final = set()
    for p in selected:
        parts = p.split("/")
        if ".git" in parts:
            continue
        if p.endswith(".pyc"):
            continue
        if p == "MANIFEST.in":
            continue
        final.add(p)

    return {"name": contract["name"], "result": {"selected": sorted(final)}}
