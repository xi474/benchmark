"""Combine the two component JSON values under the business contract in TASK.md."""
from itertools import permutations


def _build_evidence(payload, drop=None):
    best = {}
    for source, student, buyer, strength in payload["evidence"]:
        if drop is not None and source == drop:
            continue
        key = (student, buyer)
        if key not in best:
            best[key] = {}
        if source not in best[key] or strength > best[key][source]:
            best[key][source] = strength
    return {k: sum(v.values()) for k, v in best.items()}


def _solve(payload, left, right, conf):
    students = payload["students"]
    buyers = payload["buyers"]
    n = len(students)

    adj_s = {s: set() for s in students}
    adj_b = {b: set() for b in buyers}
    for (s, b), c in conf.items():
        if c > 0:
            adj_s[s].add(b)
            adj_b[b].add(s)

    seen_s = set()
    seen_b = set()
    components = []
    for s in students:
        if s in seen_s:
            continue
        comp_s = set()
        comp_b = set()
        stack = [("s", s)]
        seen_s.add(s)
        while stack:
            kind, node = stack.pop()
            if kind == "s":
                comp_s.add(node)
                for b in adj_s[node]:
                    if b not in seen_b:
                        seen_b.add(b)
                        stack.append(("b", b))
            else:
                comp_b.add(node)
                for s2 in adj_b[node]:
                    if s2 not in seen_s:
                        seen_s.add(s2)
                        stack.append(("s", s2))
        components.append((sorted(comp_s), sorted(comp_b)))

    for comp_s, comp_b in components:
        if len(comp_s) != len(comp_b):
            return None

    covered_s = set()
    covered_b = set()
    for comp_s, comp_b in components:
        covered_s.update(comp_s)
        covered_b.update(comp_b)
    if covered_s != set(students) or covered_b != set(buyers):
        return None

    comp_matchings = []
    for comp_s, comp_b in components:
        matchings = []
        for perm in permutations(comp_b):
            if all(conf.get((s, b), 0) > 0 for s, b in zip(comp_s, perm)):
                matchings.append(list(zip(comp_s, perm)))
        if not matchings:
            return None
        comp_matchings.append(matchings)

    all_matchings = [[]]
    for matchings in comp_matchings:
        new = []
        for prefix in all_matchings:
            for m in matchings:
                new.append(prefix + m)
        all_matchings = new

    best_floor = -1
    best_total = -1
    optimal = []
    for matching in all_matchings:
        confs = [conf[(s, b)] for s, b in matching]
        floor = min(confs)
        total = sum(confs)
        if floor > best_floor or (floor == best_floor and total > best_total):
            best_floor = floor
            best_total = total
            optimal = [matching]
        elif floor == best_floor and total == best_total:
            optimal.append(matching)

    count = len(optimal)

    X = {s: left[s] for s in students}
    Y = {b: right[b] for b in buyers}
    sumX = sum(X[s] for s in students)
    sumY = sum(Y[b] for b in buyers)

    nums = []
    for matching in optimal:
        sxy = sum(X[s] * Y[b] for s, b in matching)
        nums.append(n * sxy - sumX * sumY)

    min_num = min(nums)
    max_num = max(nums)

    def buyer_vector(matching):
        m = dict(matching)
        return [m[s] for s in students]

    min_vec = None
    max_vec = None
    for matching, num in zip(optimal, nums):
        vec = buyer_vector(matching)
        if num == min_num and (min_vec is None or vec < min_vec):
            min_vec = vec
        if num == max_num and (max_vec is None or vec < max_vec):
            max_vec = vec

    forced = []
    for s in students:
        bs = set()
        for matching in optimal:
            bs.add(dict(matching)[s])
        if len(bs) == 1:
            forced.append([s, bs.pop()])
    forced.sort(key=lambda p: p[0])

    return {
        "floor": best_floor,
        "total": best_total,
        "count": count,
        "min_num": min_num,
        "max_num": max_num,
        "min_buyers": min_vec,
        "max_buyers": max_vec,
        "forced": forced,
    }


def combine(payload, left, right):
    results = []
    for drop in payload["drop"]:
        conf = _build_evidence(payload, drop)
        result = _solve(payload, left, right, conf)
        results.append({"drop": drop, "result": result})
    return results
