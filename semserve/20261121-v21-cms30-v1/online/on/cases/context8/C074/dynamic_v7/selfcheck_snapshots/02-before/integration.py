def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md.

    left  = directory_snapshots: per-round {logical_path: [files_map, visible_subdirs]}
    right = scan_precedence: per-round ordered finished logical paths
    """
    nodes = payload.get("nodes", {})
    mounts = payload.get("mounts", {})
    scans = payload.get("scans", [])
    initial = payload.get("initial", {})

    # 当前生效的节点定义（含累计替换）。
    current = {k: dict(v) for k, v in nodes.items()}

    # 当前索引：逻辑文件路径 -> 曲目 id
    index = dict(initial)

    results = []

    for round_idx, scan in enumerate(scans):
        # 本轮替换同时生效，并累计到后续轮次。
        for node_id, replacement in scan.get("replace", {}).items():
            current[node_id] = dict(replacement)

        snapshots = left[round_idx] if round_idx < len(left) else {}
        ordered = right[round_idx] if round_idx < len(right) else scan.get("finish", [])

        old_index = dict(index)

        for path in ordered:
            files_map, subdirs = snapshots.get(path, ({}, []))
            subdir_set = set(subdirs)

            prefix = path + "/"
            old_entries = {}
            for old_path in list(index.keys()):
                if old_path.startswith(prefix):
                    rest = old_path[len(prefix):]
                    entry = rest.split("/", 1)[0]
                    old_entries.setdefault(entry, []).append(old_path)

            # 直接文件按当前结果覆盖。
            for name, tid in files_map.items():
                new_path = prefix + name
                index[new_path] = tid

            # 清除已消失或被忽略的直接条目之下的旧分支。
            for entry, old_paths in old_entries.items():
                if entry not in files_map and entry not in subdir_set:
                    for old_path in old_paths:
                        index.pop(old_path, None)

        # 计算 changed。
        changed = {}
        all_ids = set()
        for tid in old_index.values():
            all_ids.add(tid)
        for tid in index.values():
            all_ids.add(tid)

        for tid in all_ids:
            old_paths = sorted(p for p, t in old_index.items() if t == tid)
            new_paths = sorted(p for p, t in index.items() if t == tid)
            if old_paths != new_paths:
                changed[tid] = [old_paths, new_paths]

        results.append({"index": dict(index), "changed": changed})

    return results
