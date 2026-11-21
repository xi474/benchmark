from itertools import product


def _add(dst, src, sign=1):
    for k, v in src.items():
        dst[k] = dst.get(k, 0) + sign * v


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    stock = dict(payload.get("stock", {}))
    offers = payload["offers"]
    prep = payload["prep"]

    # offers sorted by offer ID ascending (buy vector order)
    offers_sorted = sorted(offers, key=lambda o: o[0])
    offer_ids = [o[0] for o in offers_sorted]
    offer_prices = [o[2] for o in offers_sorted]
    offer_limits = [o[3] for o in offers_sorted]
    offer_contents = [o[1] for o in offers_sorted]

    # prep steps sorted by step ID ascending (for lexicographic tie-break)
    prep_sorted = sorted(prep, key=lambda p: p[0])
    prep_ids = [p[0] for p in prep_sorted]
    prep_consume = [p[1] for p in prep_sorted]
    prep_produce = [p[2] for p in prep_sorted]
    prep_limits = [p[3] for p in prep_sorted]

    # right is the list of baskets [cost, count, buy_vector] sorted ascending.
    baskets = right

    results = []
    for dish_ids, requirement in left:
        plan = _solve(requirement, stock, offer_ids, offer_prices,
                      offer_limits, offer_contents, prep_ids, prep_consume,
                      prep_produce, prep_limits, baskets)
        results.append({"dishes": dish_ids, "plan": plan})
    return results


def _solve(requirement, stock, offer_ids, offer_prices, offer_limits,
           offer_contents, prep_ids, prep_consume, prep_produce, prep_limits,
           baskets):
    # Try baskets in the given (already optimal) order; for each basket, find
    # the best prep sequence. The first basket that yields a feasible plan is
    # optimal because baskets are sorted by (cost, count, buy_vector).
    for cost, _count, buy in baskets:
        # materials available after purchase + stock
        avail = dict(stock)
        for i, c in enumerate(buy):
            if c:
                _add(avail, offer_contents[i], c)

        plan = _best_prep(requirement, avail, prep_ids, prep_consume,
                          prep_produce, prep_limits)
        if plan is not None:
            steps, left = plan
            return {
                "cost": cost,
                "buy": buy,
                "steps": steps,
                "left": left,
            }
    return None


def _best_prep(requirement, avail, prep_ids, prep_consume, prep_produce,
               prep_limits):
    """Find lexicographically smallest step sequence (by step ID) that reaches
    requirement, minimizing total step count first, then step ID sequence."""
    n = len(prep_ids)
    # total steps <= 16
    max_steps = 16

    # BFS over states keyed by (counts used per prep, materials). We search by
    # increasing total steps, then lexicographic step sequence.
    # State: tuple of used counts per prep (length n), and material dict.
    from collections import deque

    # We'll do BFS by number of steps. To get lexicographic order among equal
    # length sequences, we generate sequences in lexicographic order via
    # iterative deepening with ordered expansion.
    start_used = tuple([0] * n)
    start_mats = tuple(sorted(avail.items()))

    # Check if already satisfied
    if _satisfied(requirement, avail):
        return [], _leftover(requirement, avail)

    # Iterative deepening on total steps
    for total in range(1, max_steps + 1):
        found = _dfs(0, total, start_used, avail, requirement, prep_ids,
                     prep_consume, prep_produce, prep_limits, [])
        if found is not None:
            steps, left = found
            return steps, left
    return None


def _dfs(depth, total, used, avail, requirement, prep_ids, prep_consume,
         prep_produce, prep_limits, seq):
    if depth == total:
        if _satisfied(requirement, avail):
            return list(seq), _leftover(requirement, avail)
        return None
    for i in range(len(prep_ids)):
        if used[i] >= prep_limits[i]:
            continue
        # check consume available
        if not _can_consume(prep_consume[i], avail):
            continue
        new_avail = dict(avail)
        _add(new_avail, prep_consume[i], -1)
        _add(new_avail, prep_produce[i], 1)
        new_used = list(used)
        new_used[i] += 1
        seq.append(prep_ids[i])
        res = _dfs(depth + 1, total, tuple(new_used), new_avail, requirement,
                   prep_ids, prep_consume, prep_produce, prep_limits, seq)
        if res is not None:
            return res
        seq.pop()
    return None


def _can_consume(consume, avail):
    return all(avail.get(k, 0) >= v for k, v in consume.items())


def _satisfied(requirement, avail):
    return all(avail.get(k, 0) >= v for k, v in requirement.items())


def _leftover(requirement, avail):
    left = {}
    for k, v in avail.items():
        need = requirement.get(k, 0)
        rem = v - need
        if rem > 0:
            left[k] = rem
    return left
