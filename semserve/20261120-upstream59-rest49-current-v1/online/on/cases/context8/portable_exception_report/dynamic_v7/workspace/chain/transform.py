import copy

try:
    from .model import load_payload
except ImportError:
    from model import load_payload


def _require_str(value, where):
    if not isinstance(value, str):
        raise ValueError(f"{where}: expected string")
    if not value.strip():
        raise ValueError(f"{where}: string must be non-empty after strip")
    return value


def _require_bool(value, where):
    if not isinstance(value, bool):
        raise ValueError(f"{where}: expected bool")
    return value


def _validate_node(node, where):
    if not isinstance(node, dict):
        raise ValueError(f"{where}: expected object")
    for key in ("id", "type", "message"):
        if key not in node:
            raise ValueError(f"{where}: missing required field {key!r}")
        _require_str(node[key], f"{where}.{key}")
    for key in ("cause", "context"):
        if key not in node:
            raise ValueError(f"{where}: missing required field {key!r}")
        v = node[key]
        if v is not None:
            _require_str(v, f"{where}.{key}")
    if "suppress_context" not in node:
        raise ValueError(f"{where}: missing required field 'suppress_context'")
    _require_bool(node["suppress_context"], f"{where}.suppress_context")
    if "frames" not in node:
        raise ValueError(f"{where}: missing required field 'frames'")
    frames = node["frames"]
    if not isinstance(frames, list):
        raise ValueError(f"{where}.frames: expected list")
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"{where}.frames[{i}]: expected object")
        for key in ("file", "function"):
            if key not in frame:
                raise ValueError(f"{where}.frames[{i}]: missing {key!r}")
            _require_str(frame[key], f"{where}.frames[{i}].{key}")
        if "line" not in frame:
            raise ValueError(f"{where}.frames[{i}]: missing 'line'")
        line = frame["line"]
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            raise ValueError(f"{where}.frames[{i}].line: expected int >= 1")
        if "locals" not in frame:
            raise ValueError(f"{where}.frames[{i}]: missing 'locals'")
        if not isinstance(frame["locals"], dict):
            raise ValueError(f"{where}.frames[{i}].locals: expected object")


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    if "name" not in contract:
        raise ValueError("contract missing 'name'")
    inputs = contract.get("inputs")
    if not isinstance(inputs, list):
        raise ValueError("contract missing 'inputs' list")
    if len(payloads) != len(inputs):
        raise ValueError("payload count must match contract inputs")

    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    if "root" not in payload:
        raise ValueError("payload missing 'root'")
    root_id = _require_str(payload["root"], "root")
    if "nodes" not in payload:
        raise ValueError("payload missing 'nodes'")
    nodes = payload["nodes"]
    if not isinstance(nodes, list):
        raise ValueError("nodes must be a list")

    by_id = {}
    for i, node in enumerate(nodes):
        _validate_node(node, f"nodes[{i}]")
        nid = node["id"]
        if nid in by_id:
            raise ValueError(f"duplicate node id {nid!r}")
        by_id[nid] = node

    if root_id not in by_id:
        raise ValueError(f"root node {root_id!r} not found")

    chain = []
    seen = set()
    current_id = root_id
    while True:
        if current_id in seen:
            raise ValueError("cycle detected in exception chain")
        seen.add(current_id)
        if len(chain) >= 8:
            raise ValueError("chain length exceeds limit of 8")
        node = by_id[current_id]
        cause = node["cause"]
        context = node["context"]
        suppress = node["suppress_context"]
        if cause is not None:
            link = "cause"
            next_id = cause
        elif context is not None and not suppress:
            link = "context"
            next_id = context
        else:
            link = None
            next_id = None
        chain.append({
            "id": node["id"],
            "type": node["type"],
            "message": node["message"],
            "link": link,
        })
        if next_id is None:
            break
        if next_id not in by_id:
            raise ValueError(f"link target {next_id!r} not found")
        current_id = next_id

    return {"name": contract["name"], "result": {"chain": chain}}
