"""C058 integration: combine host_conditions and handler_bindings into final result."""

STAGES = ("pre", "roles", "includes", "tasks", "post")


def _is_block(item):
    return isinstance(item, dict) and "block" in item


def _is_task(item):
    return isinstance(item, dict) and "id" in item


def _satisfies(only, host):
    return only is None or host in only


def _path_key(path):
    return tuple(int(x) for x in path.split("/"))


def _walk(item, path, host, table):
    """Return list of node descriptors in canonical pre-order for one host."""
    if _is_block(item):
        only = item.get("only")
        executable = _satisfies(only, host)
        block = item["block"]
        table[path] = [executable, False]
        nodes = [{"path": path, "kind": "block", "branch": None,
                  "executable": executable, "block": block}]
        for branch, key in enumerate(("tasks", "rescue", "always")):
            for j, sub in enumerate(block.get(key, []) or []):
                sub_path = "%s/%d/%d" % (path, branch, j)
                nodes.extend(_walk(sub, sub_path, host, table))
        return nodes
    else:
        only = item.get("only")
        fail_hosts = item.get("fail_hosts") or []
        executable = _satisfies(only, host)
        will_fail = host in fail_hosts
        table[path] = [executable, will_fail]
        return [{"path": path, "kind": "task", "branch": None,
                 "executable": executable, "will_fail": will_fail,
                 "task": item}]


def _build_nodes(payload, host, table):
    program = payload.get("program") or {}
    nodes = []
    for s, stage in enumerate(STAGES):
        items = program.get(stage) or []
        for i, item in enumerate(items):
            nodes.extend(_walk(item, "%d/%d" % (s, i), host, table))
    return nodes


def combine(payload, left, right):
    """Combine host_conditions (left) and handler_bindings (right)."""
    return _simulate(payload, left, right)


def _simulate(payload, left, right):
    hosts = payload.get("hosts") or []
    handlers = payload.get("handlers") or []
    handler_order = right[0] if isinstance(right, list) and right else {}
    leaf_notify = right[1] if isinstance(right, list) and len(right) > 1 else {}

    program = payload.get("program") or {}

    # Build per-host canonical event sequence: list of (stage_idx, nodes).
    host_events = {}
    for host in hosts:
        table = left.get(host, {})
        events = []
        for s, stage in enumerate(STAGES):
            items = program.get(stage) or []
            stage_nodes = []
            for i, item in enumerate(items):
                stage_nodes.extend(_walk(item, "%d/%d" % (s, i), host, table))
            events.append((s, stage_nodes))
        host_events[host] = events

    # Per-host state.
    state = {}
    for host in hosts:
        state[host] = {
            "stage_idx": 0,
            "node_idx": 0,
            "failed": False,
            "pending": [],
            "done": False,
        }

    batches = []
    final = {h: "ok" for h in hosts}

    def next_node(host):
        st = state[host]
        if st["failed"] or st["done"]:
            return None
        while st["stage_idx"] < len(STAGES):
            s = st["stage_idx"]
            stage_nodes = host_events[host][s][1]
            if st["node_idx"] < len(stage_nodes):
                return ("node", s, st["node_idx"], stage_nodes[st["node_idx"]])
            return ("flush", s, None, None)
        st["done"] = True
        return None

    def pos_key(n):
        if n[0] == "flush":
            return (n[1], float("inf"))
        return (n[1], n[2])

    while True:
        ready = {}
        for host in hosts:
            n = next_node(host)
            if n is not None:
                ready[host] = n
        if not ready:
            break

        min_key = min(pos_key(n) for n in ready.values())
        advancing = [h for h in hosts if h in ready and pos_key(ready[h]) == min_key]

        for host in advancing:
            n = ready[host]
            st = state[host]
            if n[0] == "flush":
                s = n[1]
                if st["pending"]:
                    seen = set()
                    names = []
                    for name in st["pending"]:
                        if name not in seen:
                            seen.add(name)
                            names.append(name)
                    names.sort(key=lambda nm: handler_order.get(nm, len(handlers)))
                    batches.append({
                        "host": host,
                        "task": None,
                        "kind": "flush",
                        "status": "ok",
                        "handlers": names,
                    })
                    for nm in names:
                        batches.append({
                            "host": host,
                            "task": nm,
                            "kind": "handler",
                            "status": "ok",
                        })
                    st["pending"] = []
                st["stage_idx"] += 1
                st["node_idx"] = 0
            else:
                node = n[3]
                st["node_idx"] = n[2] + 1
                if node["kind"] == "block":
                    continue
                task = node["task"]
                if not node["executable"]:
                    continue
                if node["will_fail"]:
                    status = "failed"
                else:
                    status = "ok"
                batches.append({
                    "host": host,
                    "task": task.get("id"),
                    "kind": "task",
                    "status": status,
                })
                if status == "ok":
                    for nm in task.get("notify") or []:
                        st["pending"].append(nm)
                else:
                    st["failed"] = True
                    final[host] = "failed"

    return {"batches": batches, "final": final}
