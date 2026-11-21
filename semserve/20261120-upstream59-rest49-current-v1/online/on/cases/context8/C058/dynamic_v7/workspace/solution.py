"""C058 multi-host task execution, failure recovery, and pending notifications."""

import json


def load_payload(input_path):
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def _satisfies_only(only, host):
    if only is None:
        return True
    return host in only


def transform(payload):
    hosts = list(payload.get("hosts", []))
    handlers = list(payload.get("handlers", []))
    program = payload.get("program", {}) or {}

    stages = ["pre", "roles", "includes", "tasks", "post"]

    batches = []
    final = {h: "ok" for h in hosts}

    # Per-host state: whether the host has failed (uncaught) and thus stops.
    host_failed = {h: False for h in hosts}

    for stage in stages:
        stage_nodes = program.get(stage, [])
        if not stage_nodes:
            continue

        # Build the canonical ordered list of program nodes for this stage.
        nodes = []
        _expand_stage(stage_nodes, nodes, ())

        # Per-host notification set for this stage (dedup, ordered by first
        # occurrence).
        host_notify = {h: [] for h in hosts}
        host_notify_seen = {h: set() for h in hosts}

        # Per-host pointer into nodes (next ready node index).
        host_ptr = {h: 0 for h in hosts}

        # Per-host block state keyed by block prefix path.
        host_block_state = {h: {} for h in hosts}

        while True:
            candidates = []
            for h in hosts:
                if host_failed[h]:
                    continue
                ptr = host_ptr[h]
                if ptr < len(nodes):
                    candidates.append((nodes[ptr]["path"], h))
            if not candidates:
                break

            min_path = min(p for p, _ in candidates)
            active_hosts = [h for p, h in candidates if p == min_path]

            for h in active_hosts:
                node = nodes[host_ptr[h]]
                host_ptr[h] += 1
                _execute_node(
                    node, h, hosts, handlers, batches,
                    host_notify, host_notify_seen, host_failed,
                    host_block_state,
                )

        # Flush notifications for hosts that have any (even if failed).
        for h in hosts:
            if host_notify[h]:
                flush_handlers = list(host_notify[h])
                batches.append({
                    "host": h,
                    "task": None,
                    "kind": "flush",
                    "status": "ok",
                    "handlers": flush_handlers,
                })
                for hname in flush_handlers:
                    batches.append({
                        "host": h,
                        "task": hname,
                        "kind": "handler",
                        "status": "ok",
                    })

    for h in hosts:
        if host_failed[h]:
            final[h] = "failed"

    return {"batches": batches, "final": final}


def _expand_stage(stage_nodes, nodes, prefix):
    for i, item in enumerate(stage_nodes):
        if "block" in item:
            block = item["block"]
            only = item.get("only")
            for j, t in enumerate(block.get("tasks", [])):
                nodes.append(_make_task_node(t, prefix + (i, 0, j), only))
            for j, t in enumerate(block.get("rescue", [])):
                nodes.append(_make_task_node(t, prefix + (i, 1, j), only))
            for j, t in enumerate(block.get("always", [])):
                nodes.append(_make_task_node(t, prefix + (i, 2, j), only))
        else:
            nodes.append(_make_task_node(item, prefix + (i,), None))


def _make_task_node(task, path, block_only):
    only = task.get("only")
    if only is None:
        only = block_only
    return {
        "kind": "task",
        "path": path,
        "task": task.get("id"),
        "only": only,
        "fail_hosts": task.get("fail_hosts"),
        "notify": task.get("notify", []),
        "branch": path[-2] if len(path) >= 2 and isinstance(path[-2], int) else None,
    }


def _execute_node(node, host, hosts, handlers, batches, host_notify,
                  host_notify_seen, host_failed, host_block_state):
    if node["kind"] != "task":
        return

    if not _satisfies_only(node["only"], host):
        return

    fail_hosts = node["fail_hosts"]
    failed = fail_hosts is not None and host in fail_hosts

    if failed:
        batches.append({
            "host": host,
            "task": node["task"],
            "kind": "task",
            "status": "failed",
        })
        _handle_failure(node, host, host_failed, host_block_state)
        return

    batches.append({
        "host": host,
        "task": node["task"],
        "kind": "task",
        "status": "ok",
    })
    for name in node["notify"]:
        if name not in host_notify_seen[host]:
            host_notify_seen[host].add(name)
            host_notify[host].append(name)


def _handle_failure(node, host, host_failed, host_block_state):
    path = node["path"]
    branch = node["branch"]
    if branch is None:
        host_failed[host] = True
        return

    block_prefix = path[:-2]
    state = host_block_state.setdefault(host, {}).setdefault(block_prefix, {
        "normal_failed": False,
        "rescue_done": False,
        "rescue_success": False,
    })

    if branch == 0:
        state["normal_failed"] = True
    elif branch == 1:
        state["rescue_done"] = True
        state["rescue_success"] = False
        host_failed[host] = True
    elif branch == 2:
        host_failed[host] = True
