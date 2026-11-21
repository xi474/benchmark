def compute(payload):
    """按扫描轮次生成映射，从每个完成目录的逻辑路径映射至 [保留文件映射,可见子目录名升序数组]。按轮累计替换节点。"""
    nodes = payload.get("nodes", {})
    mounts = payload.get("mounts", {})
    scans = payload.get("scans", [])

    # 当前生效的节点定义（含累计替换）。
    current = {k: dict(v) for k, v in nodes.items()}

    def resolve(path):
        """将逻辑路径解析为节点 id。路径以挂载名开始，用 / 相连。"""
        parts = path.split("/")
        node_id = mounts[parts[0]]
        for name in parts[1:]:
            node = current[node_id]
            node_id = node["dirs"][name]
        return node_id

    result = []
    for scan in scans:
        # 本轮替换同时生效，并累计到后续轮次。
        for node_id, replacement in scan.get("replace", {}).items():
            current[node_id] = dict(replacement)

        round_map = {}
        for path in scan.get("finish", []):
            node = current[resolve(path)]
            ignore = set(node.get("ignore", []))
            files = {name: tid for name, tid in node.get("files", {}).items() if name not in ignore}
            subdirs = sorted(name for name in node.get("dirs", {}) if name not in ignore)
            round_map[path] = [files, subdirs]
        result.append(round_map)

    return result
