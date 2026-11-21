import json


def transform(payloads, contract):
    """portable_frames operation.

    payloads must match contract['inputs'] order and count. Returns
    {"name": contract["name"], "result": {...}}.
    """
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    inputs = contract.get("inputs")
    if not isinstance(inputs, list) or len(payloads) != len(inputs):
        raise ValueError("payload count must match contract inputs")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("nodes must be a list")

    frames_out = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("node must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node id must be a non-empty string")
        raw_frames = node.get("frames")
        if not isinstance(raw_frames, list):
            raise ValueError("node frames must be a list")
        converted = []
        for frame in raw_frames:
            if not isinstance(frame, dict):
                raise ValueError("frame must be an object")
            converted.append(_convert_frame(frame))
        frames_out[node_id] = converted

    return {"name": contract["name"], "result": {"frames": frames_out}}


def _convert_frame(frame):
    file_ = frame.get("file")
    if not isinstance(file_, str) or not file_.strip():
        raise ValueError("frame file must be a non-empty string")
    file_ = file_.replace("\\", "/")
    file_ = file_.rsplit("/", 1)[-1]

    line = frame.get("line")
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        raise ValueError("frame line must be a positive integer")

    function = frame.get("function")
    if not isinstance(function, str) or not function.strip():
        raise ValueError("frame function must be a non-empty string")

    locals_ = frame.get("locals")
    if not isinstance(locals_, dict):
        raise ValueError("frame locals must be an object")

    serialized = {}
    for key, value in locals_.items():
        serialized[key] = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )

    return {
        "file": file_,
        "line": line,
        "function": function,
        "locals": serialized,
    }
