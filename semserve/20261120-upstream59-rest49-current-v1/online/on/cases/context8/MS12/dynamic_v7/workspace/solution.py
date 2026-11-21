from pathlib import Path
import json


def transform(payload):
    recipes = payload["recipes"]
    groups = payload["groups"]
    delivery = payload["delivery"]
    budget = payload["budget"]
    scenarios = payload["scenarios"]

    usable = []
    for r in recipes:
        if r["difficulty"] > 4:
            continue
        ing = set(r["ingredients"])
        ok = True
        for g in groups:
            if ing & set(g[2]):
                ok = False
                break
        if ok:
            usable.append(r)

    sat = {}
    for r in usable:
        s = []
        for g in groups:
            s.append(1 if r["cat"] in set(g[3]) else 0)
        sat[r["id"]] = s

    D = len(scenarios[0]["signals"])

    prefix_set = set()
    for sc in scenarios:
        sig = sc["signals"]
        for d in range(1, D + 1):
            prefix_set.add(tuple(sig[:d]))

    histories = sorted(prefix_set)
    prefix_index = {p: i for i, p in enumerate(histories)}

    def available_recipes(prefix):
        label = prefix[-1]
        avail_ing = set(delivery[label])
        out = []
        for r in usable:
            if set(r["ingredients"]) <= avail_ing:
                out.append(r)
        return out

    prefix_options = []
    for p in histories:
        opts = []
        for r in available_recipes(p):
            opts.append((r["id"], r["cost"], sat[r["id"]]))
        prefix_options.append(opts)

    scenario_paths = []
    for sc in scenarios:
        sig = sc["signals"]
        path = [prefix_index[tuple(sig[:d + 1])] for d in range(D)]
        scenario_paths.append((sc["weight"], path))

    n_prefix = len(histories)
    n_groups = len(groups)
    S = len(scenarios)

    scenario_days = []
    for weight, path in scenario_paths:
        scenario_days.append((weight, list(enumerate(path))))

    cat_of = {r["id"]: r["cat"] for r in usable}

    used_ids = [set() for _ in range(S)]
    last_cat = [None] * S
    cost_sum = [0] * S
    sat_sum = [[0] * n_groups for _ in range(S)]
    assignment = [None] * n_prefix

    prefix_affected = []
    for idx in range(n_prefix):
        aff = []
        for si, (weight, days) in enumerate(scenario_days):
            for day, pidx in days:
                if pidx == idx:
                    aff.append((si, day))
        prefix_affected.append(aff)

    best = None
    all_best = []

    def evaluate():
        floor = None
        utility = 0
        cost = 0
        for si, (weight, _) in enumerate(scenario_days):
            m = min(sat_sum[si])
            if floor is None or m < floor:
                floor = m
            utility += weight * sum(sat_sum[si][g] * groups[g][1] for g in range(n_groups))
            cost += weight * cost_sum[si]
        return floor, utility, cost

    def dfs(idx):
        nonlocal best
        if idx == n_prefix:
            floor, utility, cost = evaluate()
            key = (floor, utility, -cost)
            if best is None or key > best[0]:
                best = (key, tuple(assignment))
                all_best.clear()
                all_best.append(tuple(assignment))
            elif key == best[0]:
                all_best.append(tuple(assignment))
            return

        aff = prefix_affected[idx]
        for opt_i, (rid, cost, svec) in enumerate(prefix_options[idx]):
            ok = True
            for si, day in aff:
                if rid in used_ids[si]:
                    ok = False
                    break
                cat = cat_of[rid]
                if last_cat[si] is not None and last_cat[si] == cat:
                    ok = False
                    break
                if cost_sum[si] + cost > budget:
                    ok = False
                    break
            if not ok:
                continue

            assignment[idx] = opt_i
            saved = []
            for si, day in aff:
                saved.append((si, last_cat[si], cost_sum[si], tuple(sat_sum[si])))
                used_ids[si].add(rid)
                last_cat[si] = cat_of[rid]
                cost_sum[si] += cost
                for g in range(n_groups):
                    sat_sum[si][g] += svec[g]
            dfs(idx + 1)
            for si, day in aff:
                used_ids[si].discard(rid)
            for si, lc, cs, ss in saved:
                last_cat[si] = lc
                cost_sum[si] = cs
                sat_sum[si] = list(ss)
            assignment[idx] = None

    dfs(0)

    if best is None:
        return {"histories": [list(p) for p in histories], "optimal": None}

    floor, utility, negcost = best[0]
    cost = -negcost

    def menu_of(assign):
        return [prefix_options[i][assign[i]][0] for i in range(n_prefix)]

    best_menu = None
    for assign in all_best:
        m = menu_of(assign)
        if best_menu is None or m < best_menu:
            best_menu = m

    allowed = []
    for i in range(n_prefix):
        ids = set()
        for assign in all_best:
            ids.add(prefix_options[i][assign[i]][0])
        allowed.append(sorted(ids))

    return {
        "histories": [list(p) for p in histories],
        "optimal": {
            "floor": floor,
            "utility": utility,
            "cost": cost,
            "count": len(all_best),
            "menu": best_menu,
            "allowed": allowed,
        },
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
