"""host_conditions: per-host node table of [executable, will_fail] by tree position.

Tree positions are integer levels joined by "/". The five program stages are
pre/roles/includes/tasks/post (indices 0..4). Within a block, the normal,
rescue and always branches are indices 0/1/2 respectively.
"""

STAGES = ("pre", "roles", "includes", "tasks", "post")


def _satisfies(only, host):
    return only is None or host in only


def _walk(item, path, host, table):
    if isinstance(item, dict) and "block" in item:
        only = item.get("only")
        table[path] = [_satisfies(only, host), False]
        block = item["block"]
        for branch, key in enumerate(("tasks", "rescue", "always")):
            for j, sub in enumerate(block.get(key, []) or []):
                _walk(sub, "%s/%d/%d" % (path, branch, j), host, table)
    else:
        only = item.get("only")
        fail_hosts = item.get("fail_hosts") or []
        table[path] = [_satisfies(only, host), host in fail_hosts]


def compute(payload):
    """每个 host 对应一张节点表，按树位置（各级整数以 / 分隔）记录 [可执行,会失败]；包含块节点。"""
    hosts = payload.get("hosts") or []
    program = payload.get("program") or {}
    result = {}
    for host in hosts:
        table = {}
        for s, stage in enumerate(STAGES):
            items = program.get(stage) or []
            for i, item in enumerate(items):
                _walk(item, "%d/%d" % (s, i), host, table)
        result[host] = table
    return result
