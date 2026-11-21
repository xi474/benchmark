import base64


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    parts = payload["parts"]
    out_parts = []
    for part in parts:
        encoding = part.get("encoding")
        if encoding not in ("raw", "base64"):
            raise ValueError("unknown encoding")
        new_part = dict(part)
        raw = bytes.fromhex(part["hex"])
        if encoding == "raw":
            payload_bytes = raw
        else:
            b64 = base64.b64encode(raw).decode("ascii")
            payload_bytes = _wrap(b64).encode("ascii")
        new_part["payload_hex"] = payload_bytes.hex()
        out_parts.append(new_part)
    return {"name": contract["name"], "result": {"parts": out_parts}}


def _wrap(s):
    return "\r\n".join(s[i:i + 76] for i in range(0, len(s), 76))
