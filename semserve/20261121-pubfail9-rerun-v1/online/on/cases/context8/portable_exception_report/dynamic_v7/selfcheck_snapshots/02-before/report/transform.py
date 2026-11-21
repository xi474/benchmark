import math


def _check_finite(obj):
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("non-finite number not allowed")
    elif isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_finite(v)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    chain_payload = payloads[0]
    frames_payload = payloads[1]

    # Unwrap name/result envelope if present.
    def unwrap(p):
        if isinstance(p, dict) and set(p) == {"name", "result"}:
            return p["result"]
        return p

    chain = unwrap(chain_payload)
    frames = unwrap(frames_payload)

    if not isinstance(chain, dict):
        raise ValueError("chain input must be object")
    if not isinstance(frames, dict):
        raise ValueError("frames input must be object")
    _check_finite(chain)
    _check_finite(frames)

    chain_list = chain["chain"]
    frames_map = frames["frames"]

    nodes = []
    lines = []

    for i, item in enumerate(chain_list):
        eid = item["id"]
        link = item["link"]
        if i > 0:
            if link == "cause":
                lines.append("--- direct cause ---")
            elif link == "context":
                lines.append("--- during handling ---")
            else:
                raise ValueError("invalid link")

        node_frames = frames_map.get(eid, [])
        for fr in node_frames:
            lines.append(
                "  %s:%s in %s" % (fr["file"], fr["line"], fr["function"])
            )
        lines.append("%s: %s" % (item["type"], item["message"]))

        nodes.append(
            {
                "id": item["id"],
                "type": item["type"],
                "message": item["message"],
                "link": link,
                "frames": node_frames,
            }
        )

    text = "\n".join(lines)
    if text:
        text += "\n"

    return {"name": contract["name"], "result": {"nodes": nodes, "text": text}}
