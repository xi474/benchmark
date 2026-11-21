"""Combine the two component JSON values under the business contract in TASK.md."""


def _solve_block(students, buyers, weights):
    """Enumerate all perfect matchings of one connected block.

    weights maps (student, buyer) -> confidence. Returns list of (matching, floor, total)
    where matching is a dict student->buyer.
    """
    # students and buyers are lists in this block; weights only has valid pairs.
    n = len(students)
    assert n == len(buyers)

    # Build adjacency: for each student, list of (buyer_index, weight)
    adj = []
    for s in students:
        row = []
        for j, b in enumerate(buyers):
            w = weights.get((s, b))
            if w is not None:
                row.append((j, w))
        adj.append(row)

    results = []
    used = [False] * n
    cur = {}

    def rec(i, minw, total):
        if i == n:
            results.append((dict(cur), minw, total))
            return
        for j, w in adj[i]:
            if not used[j]:
                used[j] = True
                cur[students[i]] = buyers[j]
                rec(i + 1, min(minw, w), total + w)
                del cur[students[i]]
                used[j] = False

    rec(0, float("inf"), 0)
    return results


def _best_matchings(students, buyers, weights):
    """Return all matchings achieving max floor then max total."""
    results = _solve_block(students, buyers, weights)
    if not results:
        return []
    best_floor = max(r[1] for r in results)
    cand = [r for r in results if r[1] == best_floor]
    best_total = max(r[2] for r in cand)
    return [r[0] for r in cand if r[2] == best_total]


def _connected_components(students, buyers, weights):
    """Split the evidence bipartite graph into connected components."""
    # nodes: students indexed 0..ns-1, buyers indexed ns..ns+nb-1
    ns = len(students)
    nb = len(buyers)
    s_idx = {s: i for i, s in enumerate(students)}
    b_idx = {b: i for i, b in enumerate(buyers)}

    parent = list(range(ns + nb))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for (s, b) in weights:
        union(s_idx[s], ns + b_idx[b])

    comps = {}
    for i in range(ns):
        comps.setdefault(find(i), []).append(("s", i))
    for i in range(nb):
        comps.setdefault(find(ns + i), []).append(("b", i))

    out = []
    for root, members in comps.items():
        cs = [students[i] for (t, i) in members if t == "s"]
        cb = [buyers[i] for (t, i) in members if t == "b"]
        out.append((cs, cb))
    return out


def _compute_result(payload, left, right):
    students = payload["students"]
    buyers = payload["buyers"]
    n = len(students)

    # X per student (from left), Y per buyer (from right)
    X = {s: left[s] for s in students}
    Y = {b: right[b] for b in buyers}

    # Build evidence weights: per source max, then sum across sources.
    per_source = {}
    for source, s, b, strength in payload["evidence"]:
        key = (source, s, b)
        if key not in per_source or strength > per_source[key]:
            per_source[key] = strength

    weights = {}
    for (source, s, b), strength in per_source.items():
        weights[(s, b)] = weights.get((s, b), 0) + strength

    # Split into connected components and solve each independently.
    comps = _connected_components(students, buyers, weights)
    block_solutions = []
    for cs, cb in comps:
        if len(cs) != len(cb):
            return None  # no perfect matching possible
        sols = _best_matchings(cs, cb, weights)
        if not sols:
            return None
        block_solutions.append(sols)

    # Combine block solutions into full matchings.
    full_matchings = [{}]
    for sols in block_solutions:
        new = []
        for m in full_matchings:
            for sm in sols:
                merged = dict(m)
                merged.update(sm)
                new.append(merged)
        full_matchings = new

    if not full_matchings:
        return None

    # Compute numerator for each matching.
    def numerator(m):
        # m: student -> buyer
        sx = sum(X[s] for s in students)
        sy = sum(Y[m[s]] for s in students)
        sxy = sum(X[s] * Y[m[s]] for s in students)
        return n * sxy - sx * sy

    nums = [numerator(m) for m in full_matchings]
    min_num = min(nums)
    max_num = max(nums)

    # Lexicographically smallest buyer vector (students sorted ascending).
    def buyer_vector(m):
        return [m[s] for s in students]

    min_vec = None
    max_vec = None
    for m, num in zip(full_matchings, nums):
        v = buyer_vector(m)
        if num == min_num and (min_vec is None or v < min_vec):
            min_vec = v
        if num == max_num and (max_vec is None or v < max_vec):
            max_vec = v

    # Forced pairs: present in all optimal matchings.
    forced = []
    for s in students:
        bs = set(m[s] for m in full_matchings)
        if len(bs) == 1:
            forced.append([s, next(iter(bs))])
    forced.sort(key=lambda p: p[0])

    # floor and total are the same across all optimal matchings.
    floor = None
    total = None
    # Recompute floor/total from a representative matching.
    rep = full_matchings[0]
    floor = min(weights[(s, rep[s])] for s in students)
    total = sum(weights[(s, rep[s])] for s in students)

    return {
        "floor": floor,
        "total": total,
        "count": len(full_matchings),
        "min_num": min_num,
        "max_num": max_num,
        "min_buyers": min_vec,
        "max_buyers": max_vec,
        "forced": forced,
    }


def combine(payload, left, right):
    out = []
    for drop in payload["drop"]:
        if drop is None:
            result = _compute_result(payload, left, right)
        else:
            # Recompute with the given source fully withdrawn.
            sub = dict(payload)
            sub["evidence"] = [e for e in payload["evidence"] if e[0] != drop]
            result = _compute_result(sub, left, right)
        out.append({"drop": drop, "result": result})
    return out
