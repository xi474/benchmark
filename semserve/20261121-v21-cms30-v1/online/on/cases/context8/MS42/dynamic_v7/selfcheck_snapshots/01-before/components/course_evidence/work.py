def compute(payload):
    """为每门课生成 [项目统计,传递可达表]；统计行 [ID,标签,[成绩和分子,分母],非空数] 按 ID 排序，保留零成绩。可达表的值为有序 ID 数组。"""
    courses = payload["courses"]
    result = {}
    for code, course in courses.items():
        items = course["items"]
        edges = course.get("edges", [])

        # Item statistics: [ID, label, [score_sum, count], non_null_count]
        stats = []
        for item in items:
            item_id, label, scores = item[0], item[1], item[2]
            total = 0
            count = 0
            for s in scores:
                if s is not None:
                    total += s
                    count += 1
            stats.append([item_id, label, [total, count], count])

        # Sort stats by ID
        stats.sort(key=lambda row: row[0])

        # Transitive reachability table
        ids = [item[0] for item in items]
        id_set = set(ids)
        # Build adjacency
        adj = {i: set() for i in ids}
        for e in edges:
            a, b = e[0], e[1]
            if a in id_set and b in id_set:
                adj[a].add(b)

        # Transitive closure via DFS from each node
        reach = {}
        for src in ids:
            seen = set()
            stack = list(adj[src])
            while stack:
                node = stack.pop()
                if node in seen:
                    continue
                seen.add(node)
                stack.extend(adj[node])
            reach[src] = sorted(seen)

        result[code] = [stats, reach]

    return result
