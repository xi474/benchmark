import re

_BOUNDARY_RE = re.compile(r"^[A-Za-z0-9-]+$")


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    snapshot = payloads[0]
    encoding = payloads[1]

    # Unwrap the encoding component's {name, result} envelope.
    if isinstance(encoding, dict) and set(encoding) == {"name", "result"}:
        encoding = encoding["result"]

    boundary = snapshot.get("boundary")
    if not isinstance(boundary, str) or not boundary:
        raise ValueError("boundary must be non-empty str")
    if not _BOUNDARY_RE.match(boundary):
        raise ValueError("boundary must match [A-Za-z0-9-]+")

    parts = encoding.get("parts")
    if not isinstance(parts, list):
        raise ValueError("encoding parts must be a list")

    # Build each part's payload bytes and check boundary collision.
    rendered = []
    for part in parts:
        payload_hex = part.get("payload_hex")
        if not isinstance(payload_hex, str):
            raise ValueError("payload_hex must be str")
        try:
            payload_bytes = bytes.fromhex(payload_hex)
        except ValueError:
            raise ValueError("invalid payload_hex")
        if boundary.encode("utf-8") in payload_bytes:
            raise ValueError("boundary appears in payload")
        rendered.append((part, payload_bytes))

    out = bytearray()
    for part, payload_bytes in rendered:
        out += b"--" + boundary.encode("utf-8") + b"\r\n"
        if part.get("encoding") == "base64":
            out += b"Content-Transfer-Encoding: base64\r\n"
        mimetype = part.get("mimetype")
        if not isinstance(mimetype, str) or not mimetype:
            raise ValueError("mimetype must be non-empty str")
        out += b"Content-Type: " + mimetype.encode("utf-8") + b"\r\n"
        name = part.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("name must be non-empty str")
        disposition = 'form-data; name="' + name + '"'
        filename = part.get("filename")
        if filename is not None:
            if not isinstance(filename, str) or not filename:
                raise ValueError("filename must be non-empty str")
            disposition += '; filename="' + filename + '"'
        out += b"Content-Disposition: " + disposition.encode("utf-8") + b"\r\n"
        out += b"\r\n"
        out += payload_bytes
        out += b"\r\n"
    out += b"--" + boundary.encode("utf-8") + b"--\r\n"

    return {
        "name": contract["name"],
        "result": {
            "content_type": "multipart/form-data; boundary=" + boundary,
            "body_hex": bytes(out).hex(),
        },
    }
