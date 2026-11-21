import hashlib
import io
import zipfile

try:
    from .model import load_payload
except ImportError:
    from model import load_payload


def _unwrap(payload):
    # When an input object has keys exactly name/result, only its result is
    # the business input; other objects are interpreted as-is.
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    modules_payload = _unwrap(payloads[0])
    closure_payload = _unwrap(payloads[1])

    if not isinstance(modules_payload, dict) or "modules" not in modules_payload:
        raise ValueError("missing modules")
    modules = modules_payload["modules"]
    if not isinstance(modules, dict):
        raise ValueError("modules must be object")

    if not isinstance(closure_payload, dict):
        raise ValueError("closure must be object")
    paths = closure_payload.get("paths")
    external = closure_payload.get("external")
    if not isinstance(paths, list):
        raise ValueError("missing paths")
    if not isinstance(external, list):
        raise ValueError("missing external")

    # Validate paths: no duplicates, all exist in modules.
    if len(set(paths)) != len(paths):
        raise ValueError("duplicate paths")
    for p in paths:
        if p not in modules:
            raise ValueError("source path not found: %s" % p)

    # Build ZIP entries sorted by path.
    entries = {}
    for p in paths:
        entries[p] = modules[p]

    root_init = "__init__.py"
    if root_init not in modules:
        entries[root_init] = ""

    sorted_paths = sorted(entries.keys())

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in sorted_paths:
            data = entries[p]
            if not isinstance(data, str):
                raise ValueError("module source must be string")
            raw = data.encode("utf-8")
            zi = zipfile.ZipInfo(p, date_time=(1980, 1, 1, 0, 0, 0))
            zi.create_system = 3
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_STORED
            zf.writestr(zi, raw)

    zip_bytes = buf.getvalue()
    sha = hashlib.sha256(zip_bytes).hexdigest()

    return {
        "name": contract["name"],
        "result": {
            "paths": sorted_paths,
            "zip_hex": zip_bytes.hex(),
            "sha256": sha,
            "external": external,
        },
    }
