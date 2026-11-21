import math


def _reject_non_finite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number")
    elif isinstance(obj, dict):
        for v in obj.values():
            _reject_non_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_non_finite(v)


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    _reject_non_finite(payloads)
    _reject_non_finite(contract)

    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")
    if "result" in data and "name" in data and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")

    contacts = data.get("contacts")
    if not isinstance(contacts, list):
        raise ValueError("contacts must be a list")

    seen = set()
    result_contacts = {}
    for c in contacts:
        if not isinstance(c, dict):
            raise ValueError("contact must be an object")
        cid = c.get("id")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError("contact id must be non-empty string")
        if cid in seen:
            raise ValueError("duplicate contact id")
        seen.add(cid)

        email = c.get("email")
        message = c.get("message")
        chat = c.get("chat")

        for field, val in (("email", email), ("message", message), ("chat", chat)):
            if val is not None:
                if not isinstance(val, str) or not val.strip():
                    raise ValueError("channel field must be null or non-empty string")

        if message is not None:
            primary = "message"
            address = message
        elif chat is not None:
            primary = "chat"
            address = chat
        else:
            primary = None
            address = None

        result_contacts[cid] = {
            "email": email,
            "primary": primary,
            "address": address,
        }

    return {"name": contract["name"], "result": {"contacts": result_contacts}}
