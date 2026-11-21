def _unwrap(payload):
    if isinstance(payload, dict) and set(payload.keys()) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count does not match contract inputs")

    chain_data = _unwrap(payloads[0])
    frames_data = _unwrap(payloads[1])

    chain = chain_data["chain"]
    frames_map = frames_data["frames"]

    nodes = []
    lines = []

    for index, item in enumerate(chain):
        link = item["link"]
        if index > 0:
            if link == "cause":
                lines.append("--- direct cause ---")
            elif link == "context":
                lines.append("--- during handling ---")
            else:
                raise ValueError("invalid link for non-first chain item")

        node_frames = frames_map.get(item["id"], [])
        for frame in node_frames:
            lines.append(
                "  %s:%d in %s" % (frame["file"], frame["line"], frame["function"])
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
