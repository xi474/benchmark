def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    topics = payload["topics"]

    # left: per-topic score table (list of dicts mapping paper id -> max quality)
    # right: deduped, sorted existing graph triples
    if not topics:
        return {"review": [], "graph": right}

    # Build candidate options per topic: list of (paper_id, quality)
    options = [sorted(topic_scores.items(), key=lambda kv: kv[0]) for topic_scores in left]

    n = len(topics)
    best = None  # (min_q, total_q, id_tuple)

    def better(candidate, current):
        if current is None:
            return True
        c_min, c_total, c_ids = candidate
        k_min, k_total, k_ids = current
        if c_min != k_min:
            return c_min > k_min
        if c_total != k_total:
            return c_total > k_total
        return c_ids < k_ids  # lexicographically smaller id sequence wins

    def search(i, used, chosen, min_q, total_q):
        nonlocal best
        if i == n:
            candidate = (min_q, total_q, tuple(chosen))
            if better(candidate, best):
                best = candidate
            return
        for pid, q in options[i]:
            if pid in used:
                continue
            used.add(pid)
            chosen.append(pid)
            search(i + 1, used, chosen, min(min_q, q), total_q + q)
            chosen.pop()
            used.remove(pid)

    search(0, set(), [], float("inf"), 0)

    if best is None:
        return None

    _, _, id_tuple = best
    review = []
    for i in range(n):
        pid = id_tuple[i]
        q = next(qq for p, qq in options[i] if p == pid)
        review.append([topics[i], pid, q])

    # Build graph: existing edges + supports edges, dedup, sort lexicographically
    edges = set(tuple(triple) for triple in right)
    for i in range(n):
        edges.add((id_tuple[i], "supports", topics[i]))
    graph = sorted(edges)

    return {"review": review, "graph": [list(t) for t in graph]}
