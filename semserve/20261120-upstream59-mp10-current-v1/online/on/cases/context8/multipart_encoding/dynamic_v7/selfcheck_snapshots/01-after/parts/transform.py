import re
from pathlib import Path

FIELD_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
MIME_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+/[A-Za-z0-9!#$%&'*+.^_`|~-]+$")

_EXT_MIME = {
    ".txt": "text/plain",
    ".json": "application/json",
    ".jpg": "image/jpeg",
}


def _basename(filename):
    return filename.rsplit("/", 1)[-1]


def _mime_for(filename, explicit):
    if explicit is not None:
        return explicit
    if filename is not None:
        for ext, mime in _EXT_MIME.items():
            if filename.lower().endswith(ext):
                return mime
    return "application/octet-stream"


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]

    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "name" in payload and "result" in payload and set(payload) == {"name", "result"}:
        payload = payload["result"]

    fields = payload.get("fields")
    files = payload.get("files")
    boundary = payload.get("boundary")

    if not isinstance(fields, dict):
        raise ValueError("fields must be object")
    if not isinstance(files, dict):
        raise ValueError("files must be object")
    if not isinstance(boundary, str) or not boundary.strip():
        raise ValueError("boundary must be non-empty str")
    if not re.fullmatch(r"[A-Za-z0-9-]+", boundary):
        raise ValueError("boundary invalid")

    parts = []
    for name in sorted(fields.keys()):
        if not isinstance(name, str) or not FIELD_NAME_RE.fullmatch(name):
            raise ValueError("invalid field name")
        value = fields[name]

        if isinstance(value, str):
            # plain text
            parts.append({
                "name": name,
                "filename": None,
                "mimetype": "text/plain",
                "encoding": "raw",
                "hex": value.encode("utf-8").hex(),
            })
            continue

        if not isinstance(value, dict) or not value:
            raise ValueError("field value must be str or non-empty object")

        content = value.get("content")
        filename = value.get("filename")
        mimetype = value.get("mimetype")

        if content is not None and not isinstance(content, str):
            raise ValueError("content must be str")
        if filename is not None and not isinstance(filename, str):
            raise ValueError("filename must be str")
        if mimetype is not None and not isinstance(mimetype, str):
            raise ValueError("mimetype must be str")

        if mimetype is not None and not MIME_RE.fullmatch(mimetype):
            raise ValueError("invalid mimetype")

        if content is not None:
            # inline content
            data = content.encode("utf-8")
            encoding = "raw"
            if filename is not None:
                filename = _basename(filename)
                if not FILENAME_RE.fullmatch(filename):
                    raise ValueError("invalid filename")
            mime = _mime_for(filename, mimetype)
            parts.append({
                "name": name,
                "filename": filename,
                "mimetype": mime,
                "encoding": encoding,
                "hex": data.hex(),
            })
            continue

        # only filename -> read from files, base64
        if filename is None:
            raise ValueError("empty sub-object")
        if not isinstance(filename, str):
            raise ValueError("filename must be str")
        # filename is a safe relative path key into files
        if filename not in files:
            raise ValueError("missing file")
        hexdata = files[filename]
        if not isinstance(hexdata, str):
            raise ValueError("file hex must be str")
        try:
            data = bytes.fromhex(hexdata)
        except ValueError:
            raise ValueError("invalid hex")
        base = _basename(filename)
        if not FILENAME_RE.fullmatch(base):
            raise ValueError("invalid filename")
        mime = _mime_for(base, mimetype)
        parts.append({
            "name": name,
            "filename": base,
            "mimetype": mime,
            "encoding": "base64",
            "hex": data.hex(),
        })

    return {"name": contract["name"], "result": {"parts": parts}}
