import math


def _reject_nonfinite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number not allowed")
    if isinstance(value, dict):
        for v in value.values():
            _reject_nonfinite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_nonfinite(v)
    return value


def transform(payloads, contract):
    if not isinstance(payloads, list) or len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    _reject_nonfinite(data)

    emails = data.get("emails")
    reply_email_id = data.get("reply_email_id")
    manager = data.get("manager")
    reply_text = data.get("reply_text")

    if not isinstance(emails, list):
        raise ValueError("emails must be a list")
    if not isinstance(reply_email_id, str):
        raise ValueError("reply_email_id must be a string")
    if not isinstance(manager, str):
        raise ValueError("manager must be a string")
    if not isinstance(reply_text, str):
        raise ValueError("reply_text must be a string")

    target = None
    for e in emails:
        if not isinstance(e, dict):
            raise ValueError("email must be an object")
        if e.get("id") == reply_email_id:
            target = e
            break

    if target is None:
        raise ValueError("reply target email not found")
    if target.get("sender") != manager:
        raise ValueError("reply target sender is not the manager")

    return {
        "name": contract["name"],
        "result": {
            "email_id": reply_email_id,
            "thread_id": target["thread_id"],
            "to": manager,
            "text": reply_text,
        },
    }
