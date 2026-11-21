import json
from pathlib import Path
from itertools import combinations
from collections import defaultdict


def _add(a, b, mult=1):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v * mult
    return out


def _sub(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) - v
    return out


def _ge(a, b):
    for k, v in b.items():
        if a.get(k, 0) < v:
            return False
    return True


def _positive(d):
    return {k: v for k, v in d.items() if v > 0}


def transform(payload):
    dishes = payload["dishes"]
    stock = payload["stock"]
    offers = payload["offers"]
    prep = payload["prep"]
    max_difficulty = payload["max_difficulty"]

    cand = [d for d in dishes if d[2] <= max_difficulty]

    by_cat = defaultdict(list)
    for d in cand:
        by_cat[d[1]].append(d)

    categories = sorted(by_cat.keys())

    offers_sorted = sorted(offers, key=lambda o: o[0])
    offer_ids = [o[0] for o in offers_sorted]
    offer_mats = [o[1] for o in offers_sorted]
    offer_prices = [o[2] for o in offers_sorted]
    offer_max = [o[3] for o in offers_sorted]

    prep_sorted = sorted(prep, key=lambda p: p[0])
    prep_ids = [p[0] for p in prep_sorted]
    prep_consume = [p[1] for p in prep_sorted]
    prep_produce = [p[2] for p in prep_sorted]
    prep_max = [p[3] for p in prep_sorted]

    results = []

    for cat_triple in combinations(categories, 3):
        dish_lists = [by_cat[c] for c in cat_triple]
        for combo in _product(dish_lists):
            dish_ids = sorted(d[0] for d in combo)
            required = {}
            for d in combo:
                required = _add(required, d[3])

            plan = _solve(required, stock, offers_sorted, prep_sorted,
                          offer_ids, offer_mats, offer_prices, offer_max,
                          prep_ids, prep_consume, prep_produce, prep_max)
            results.append({"dishes": dish_ids, "plan": plan})

    results.sort(key=lambda r: r["dishes"])
    return results


def _product(lists):
    if not lists:
        yield []
        return
    for head in lists[0]:
        for tail in _product(lists[1:]):
            yield [head] + tail


def _solve(required, stock, offers_sorted, prep_sorted,
           offer_ids, offer_mats, offer_prices, offer_max,
           prep_ids, prep_consume, prep_produce, prep_max):
    n_offers = len(offers_sorted)

    buy_vectors = _enumerate_buys(offer_max)

    best = None

    for buy in buy_vectors:
        mats = dict(stock)
        cost = 0
        num_packs = 0
        for i in range(n_offers):
            if buy[i] > 0:
                mats = _add(mats, offer_mats[i], buy[i])
                cost += offer_prices[i] * buy[i]
                num_packs += buy[i]

        sol = _search_prep(required, mats, prep_consume, prep_produce, prep_max,
                           prep_ids)
        if sol is None:
            continue
        steps_seq, final_mats = sol
        total_steps = len(steps_seq)

        key = (cost, num_packs, tuple(buy), total_steps, tuple(steps_seq))
        if best is None or key < best[0]:
            best = (key, buy, steps_seq, final_mats)

    if best is None:
        return None

    key, buy, steps_seq, final_mats = best
    cost, num_packs, buy_vec, total_steps, steps_key = key

    left = _positive(_sub(final_mats, required))

    return {
        "cost": cost,
        "buy": list(buy),
        "steps": steps_seq,
        "left": left,
    }


def _enumerate_buys(offer_max):
    n = len(offer_max)
    ranges = [range(m + 1) for m in offer_max]
    result = []

    def rec(i, cur):
        if i == n:
            result.append(tuple(cur))
            return
        for v in ranges[i]:
            cur.append(v)
            rec(i + 1, cur)
            cur.pop()

    rec(0, [])
    return result


def _search_prep(required, mats, prep_consume, prep_produce, prep_max, prep_ids):
    n_prep = len(prep_consume)

    def canon(m):
        return tuple(sorted((k, v) for k, v in m.items() if v != 0))

    best = None
    memo = {}

    def dfs(m, steps, depth):
        nonlocal best
        if depth > 16:
            return
        if _ge(m, required):
            if best is None or (len(steps), steps) < (len(best), best):
                best = list(steps)
            return
        c = canon(m)
        if c in memo and memo[c] <= len(steps):
            return
        memo[c] = len(steps)
        for i in range(n_prep):
            if steps.count(i) >= prep_max[i]:
                continue
            if _ge(m, prep_consume[i]):
                nm = _sub(m, prep_consume[i])
                nm = _add(nm, prep_produce[i])
                steps.append(i)
                dfs(nm, steps, depth + 1)
                steps.pop()

    dfs(dict(mats), [], 0)

    if best is None:
        return None

    m = dict(mats)
    for i in best:
        m = _sub(m, prep_consume[i])
        m = _add(m, prep_produce[i])
    return ([prep_ids[i] for i in best], m)


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
