def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    topics = payload["topics"]
    papers = payload["papers"]
    scores = left  # list of dicts, one per topic in order
    graph_facts = right  # list of [s, r, o] triples

    if not topics:
        return {"review": [], "graph": graph_facts}

    # Build candidate list per topic: (paper_id, quality)
    candidates = []
    for i, topic in enumerate(topics):
        row = scores[i]
        candidates.append([(pid, q) for pid, q in row.items()])

    # Backtracking search: maximize min quality, then total quality,
    # then lexicographically smallest paper-id sequence.
    n = len(topics)
    best = None  # (min_q, total_q, id_seq)

    used = set()

    def dfs(idx, chosen, total, min_q):
        nonlocal best
        if idx == n:
            key = (min_q, total, tuple(chosen))
            if best is None or key > best[0]:
                best = (key, list(chosen))
            return
        for pid, q in candidates[idx]:
            if pid in used:
                continue
            used.add(pid)
            chosen.append(pid)
            dfs(idx + 1, chosen, total + q, min(min_q, q))
            chosen.pop()
            used.remove(pid)

    dfs(0, [], 0, float("inf"))

    if best is None:
        return None

    _, id_seq = best
    review = []
    for i, pid in enumerate(id_seq):
        q = scores[i][pid]
        review.append([topics[i], pid, q])

    # Build graph: existing facts + supports edges, dedup, sort lexicographically.
    edges = set(tuple(t) for t in graph_facts)
    for i, pid in enumerate(id_seq):
        edges.add((pid, "supports", topics[i]))
    graph = [list(t) for t in sorted(edges)]

    return {"review": review, "graph": graph}
