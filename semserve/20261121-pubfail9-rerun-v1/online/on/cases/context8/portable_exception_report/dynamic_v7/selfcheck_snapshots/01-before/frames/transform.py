import json


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload.keys()) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("input must be object")
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("nodes must be list")
    frames = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("node must be object")
        nid = node.get("id")
        if not isinstance(nid, str) or not nid.strip():
            raise ValueError("node id must be non-empty string")
        node_frames = node.get("frames")
        if not isinstance(node_frames, list):
            raise ValueError("frames must be list")
        out_frames = []
        for fr in node_frames:
            if not isinstance(fr, dict):
                raise ValueError("frame must be object")
            file = fr.get("file")
            if not isinstance(file, str):
                raise ValueError("file must be string")
            file = file.replace("\\", "/")
            file = file.rsplit("/", 1)[-1]
            line = fr.get("line")
            if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                raise ValueError("line must be positive int")
            function = fr.get("function")
            if not isinstance(function, str) or not function.strip():
                raise ValueError("function must be non-empty string")
            locals_ = fr.get("locals")
            if not isinstance(locals_, dict):
                raise ValueError("locals must be object")
            serialized = {}
            for k, v in locals_.items():
                serialized[k] = json.dumps(
                    v, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False)
            out_frames.append({
                "file": file,
                "line": line,
                "function": function,
                "locals": serialized,
            })
        frames[nid] = out_frames
    return {"name": contract["name"], "result": {"frames": frames}}
