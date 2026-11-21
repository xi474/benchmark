from pathlib import Path
import json


def _resolve_node(nodes, mounts, path):
    """Resolve a logical path to a node id, honoring ancestor ignores."""
    parts = path.split("/")
    if not parts:
        return None
    mount_name = parts[0]
    if mount_name not in mounts:
        return None
    node_id = mounts[mount_name]
    for name in parts[1:]:
        node = nodes.get(node_id)
        if node is None:
            return None
        if name in node.get("ignore", []):
            return None
        dirs = node.get("dirs", {})
        if name not in dirs:
            return None
        node_id = dirs[name]
    return node_id


def _visible_children(nodes, node_id):
    """Return (visible_files dict, visible_dirs dict) for a node."""
    node = nodes.get(node_id)
    if node is None:
        return {}, {}
    ignored = set(node.get("ignore", []))
    files = {k: v for k, v in node.get("files", {}).items() if k not in ignored}
    dirs = {k: v for k, v in node.get("dirs", {}).items() if k not in ignored}
    return files, dirs


def transform(payload):
    nodes = payload["nodes"]
    mounts = payload["mounts"]
    index = dict(payload["initial"])

    results = []

    for scan in payload["scans"]:
        # Apply replacements (simultaneous).
        for node_id, repl in scan.get("replace", {}).items():
            nodes[node_id] = repl

        prev = dict(index)

        finish = scan.get("finish", [])

        for dir_path in finish:
            node_id = _resolve_node(nodes, mounts, dir_path)
            if node_id is None:
                continue
            files, dirs = _visible_children(nodes, node_id)

            # Overwrite direct files.
            for name, tid in files.items():
                index[dir_path + "/" + name] = tid

            # Clear stale branches under direct entries.
            prefix = dir_path + "/"
            for old_path in list(index.keys()):
                if not old_path.startswith(prefix):
                    continue
                rest = old_path[len(prefix):]
                if not rest:
                    continue
                first = rest.split("/", 1)[0]
                if first in files:
                    # file<->dir swap: deeper entries under a file are stale
                    del index[old_path]
                elif first in dirs:
                    # still-visible dir: keep old entries inside
                    continue
                else:
                    # disappeared or ignored entry
                    del index[old_path]

        # Compute changed track ids.
        changed = {}
        all_ids = set(prev.values()) | set(index.values())
        for tid in all_ids:
            old_paths = sorted(p for p, t in prev.items() if t == tid)
            new_paths = sorted(p for p, t in index.items() if t == tid)
            if old_paths != new_paths:
                changed[tid] = [old_paths, new_paths]

        results.append({"index": dict(index), "changed": changed})

    return results


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
