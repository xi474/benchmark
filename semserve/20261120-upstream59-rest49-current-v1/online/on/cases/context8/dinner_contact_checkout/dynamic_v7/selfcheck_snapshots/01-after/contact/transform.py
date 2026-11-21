def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = _unwrap(payloads[0])
    if not isinstance(data, dict):
        raise ValueError("input must be object")

    conversations = data.get("conversations")
    topic = data.get("topic")
    if not isinstance(conversations, list):
        raise ValueError("conversations must be list")
    if not isinstance(topic, str):
        raise ValueError("topic must be string")

    needle = topic.casefold()
    best = None
    for conv in conversations:
        if not isinstance(conv, dict):
            raise ValueError("conversation must be object")
        cid = conv.get("id")
        contact_id = conv.get("contact_id")
        ts = conv.get("ts")
        ctopic = conv.get("topic")
        if not isinstance(ctopic, str):
            raise ValueError("conversation topic must be string")
        if needle not in ctopic.casefold():
            continue
        if best is None or ts > best[0] or (ts == best[0] and cid < best[1]):
            best = (ts, cid, contact_id)

    if best is None:
        result = {"contact_id": None, "conversation_id": None}
    else:
        result = {"contact_id": best[2], "conversation_id": best[1]}

    return {"name": contract["name"], "result": result}
