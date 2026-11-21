"""Combine the two component JSON values under the business contract in TASK.md."""


def combine(payload, left, right):
    recipes = payload["recipes"]
    groups = payload["groups"]
    budget = payload["budget"]
    scenarios = payload["scenarios"]

    # left: list of [history, leaf_weight_or_null] sorted lexicographically.
    # right: dict signal -> list of eligible dish ids (recipe order).
    histories = [h for h, _ in left]
    eligible = right

    recipe_by_id = {r["id"]: r for r in recipes}
    group_likes = [set(g[3]) for g in groups]

    hist_index = {tuple(h): i for i, h in enumerate(histories)}

    n_hist = len(histories)
    candidates = [eligible.get(h[-1], []) for h in histories]

    sat = []
    for liked in group_likes:
        sat.append({r["id"]: (1 if r["cat"] in liked else 0) for r in recipes})

    cost_of = {r["id"]: r["cost"] for r in recipes}
    cat_of = {r["id"]: r["cat"] for r in recipes}

    scenario_paths = []
    for s in scenarios:
        sigs = s["signals"]
        idxs = [hist_index[tuple(sigs[:d])] for d in range(1, len(sigs) + 1)]
        scenario_paths.append((s["weight"], idxs))

    def evaluate(assignment):
        min_service = None
        total_utility = 0
        total_cost = 0
        for weight, idxs in scenario_paths:
            dishes = [assignment[i] for i in idxs]
            if len(set(dishes)) != len(dishes):
                return None
            for a, b in zip(dishes, dishes[1:]):
                if cat_of[a] == cat_of[b]:
                    return None
            c = sum(cost_of[d] for d in dishes)
            if c > budget:
                return None
            total_cost += weight * c
            service = None
            for gi in range(len(groups)):
                s = sum(sat[gi][d] for d in dishes)
                service = s if service is None else min(service, s)
            min_service = service if min_service is None else min(min_service, service)
            for gi in range(len(groups)):
                cnt = groups[gi][1]
                total_utility += weight * cnt * sum(sat[gi][d] for d in dishes)
        return (min_service, total_utility, total_cost)

    best_key = None
    best_assignment = None

    assignment = [None] * n_hist

    def backtrack(i):
        nonlocal best_key, best_assignment
        if i == n_hist:
            res = evaluate(assignment)
            if res is None:
                return
            floor, utility, cost = res
            key = (floor, utility, -cost)
            if best_key is None or key > best_key:
                best_key = key
                best_assignment = tuple(assignment)
            return
        for dish in candidates[i]:
            assignment[i] = dish
            backtrack(i + 1)
        assignment[i] = None

    backtrack(0)

    if best_key is None:
        return {"histories": histories, "optimal": None}

    floor, utility, neg_cost = best_key
    cost = -neg_cost

    optimal_assignments = []

    def collect(i):
        if i == n_hist:
            res = evaluate(assignment)
            if res is not None and res == (floor, utility, cost):
                optimal_assignments.append(tuple(assignment))
            return
        for dish in candidates[i]:
            assignment[i] = dish
            collect(i + 1)
        assignment[i] = None

    collect(0)

    count = len(set(optimal_assignments))
    menu = list(min(optimal_assignments))

    allowed = []
    for i in range(n_hist):
        allowed.append(sorted({a[i] for a in optimal_assignments}))

    return {
        "histories": histories,
        "optimal": {
            "floor": floor,
            "utility": utility,
            "cost": cost,
            "count": count,
            "menu": menu,
            "allowed": allowed,
        },
    }
