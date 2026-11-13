"""Exact counts of optimal apportionments and individual award changes."""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import lcm


def choices(request, fixed):
    cells = request["cells"]
    denominator = lcm(*(cell["quota"][1] for cell in cells))
    columns = list(request["cols"])
    remaining = list(request["cols"].values())
    by_row = defaultdict(list)
    for cell in cells:
        base, rest = divmod(*cell["quota"])
        if cell["id"] in fixed and not base <= fixed[cell["id"]] <= base + bool(rest):
            return None
        col = columns.index(cell["col"])
        remaining[col] -= base
        by_row[cell["row"]].append((cell, base, rest, col))
    layers = []
    for row, target in request["rows"].items():
        items = by_row[row]
        need = target - sum(base for _, base, _, _ in items)
        mandatory = {i for i, (cell, base, _, _) in enumerate(items) if fixed.get(cell["id"], base) > base}
        free = [i for i, (cell, _, rest, _) in enumerate(items) if rest and cell["id"] not in fixed]
        if not 0 <= need - len(mandatory) <= len(free):
            return None
        policies = []
        for proposed in combinations(free, need - len(mandatory)):
            up = mandatory.union(proposed)
            used = tuple(items[i][3] for i in sorted(up))
            changed = []
            loss = 0
            for i, (cell, base, _, _) in enumerate(items):
                award = base + (i in up)
                num, den = cell["quota"]
                loss += abs(award * den - num) * (denominator // den)
                if award != cell["published"]:
                    changed.append(cell["id"])
            policies.append((used, (loss, len(changed)), changed))
        layers.append(policies)
    return tuple(remaining), layers, denominator


def consume(state, columns):
    rest = list(state)
    for col in columns:
        rest[col] -= 1
        if rest[col] < 0:
            return None
    return tuple(rest)


def summarize(request, objective, denominator, count, changed):
    loss = Fraction(objective[0], denominator)
    return {"loss": [loss.numerator, loss.denominator], "changes": objective[1],
            "tables": count, "changed_in": {c["id"]: changed.get(c["id"], 0) for c in request["cells"]}}


def optimal_tables(request, fixed):
    problem = choices(request, fixed)
    if problem is None:
        return None
    initial, layers, denominator = problem

    @lru_cache(None)
    def suffix(i, state):
        if i == len(layers):
            return ((0, 0), 1) if not any(state) else (None, 0)
        best = None
        count = 0
        for cols, cost, _ in layers[i]:
            rest = consume(state, cols)
            if rest is None:
                continue
            tail, ways = suffix(i + 1, rest)
            if not ways:
                continue
            objective = cost[0] + tail[0], cost[1] + tail[1]
            if best is None or objective < best:
                best, count = objective, ways
            elif objective == best:
                count += ways
        return best, count

    best, count = suffix(0, initial)
    if not count:
        return None
    prefixes = {initial: 1}
    changed = defaultdict(int)
    for i, policies in enumerate(layers):
        following = defaultdict(int)
        for state, histories in prefixes.items():
            optimum, _ = suffix(i, state)
            for cols, cost, ids in policies:
                rest = consume(state, cols)
                if rest is None:
                    continue
                tail, completions = suffix(i + 1, rest)
                if completions and (cost[0] + tail[0], cost[1] + tail[1]) == optimum:
                    following[rest] += histories
                    for k in ids:
                        changed[k] += histories * completions
        prefixes = following
    assert sum(prefixes.values()) == count
    return summarize(request, best, denominator, count, changed)


def column_oracle(request, fixed):
    # Independent transition construction. A column must consume exactly its
    # total. Carry change tallies for all partial plans tied at an optimum.
    rows = list(request["rows"])
    initial = list(request["rows"].values())
    groups = defaultdict(list)
    den = lcm(*(c["quota"][1] for c in request["cells"]))
    for c in request["cells"]:
        base = c["quota"][0] // c["quota"][1]
        i = rows.index(c["row"])
        initial[i] -= base
        groups[c["col"]].append((c, i, base))
    states = {tuple(initial): ((0, 0), 1, {})}
    for col, total in request["cols"].items():
        items = groups[col]
        need = total - sum(b for _, _, b in items)
        if not 0 <= need <= len(items):
            return None
        options = []
        for subset in combinations(range(len(items)), need):
            picked = set(subset)
            cost = 0
            affected = []
            for k, (cell, _, base) in enumerate(items):
                num, d = cell["quota"]
                award = base + (k in picked)
                if award != fixed.get(cell["id"], award) or (k in picked and num % d == 0):
                    break
                cost += abs(num - d * award) * (den // d)
                if award != cell["published"]:
                    affected.append(cell["id"])
            else:
                options.append(([items[k][1] for k in subset], (cost, len(affected)), affected))
        new = {}
        for prev, (before, ways, tally) in states.items():
            for used, price, affected in options:
                nxt = consume(prev, used)
                if nxt is None:
                    continue
                obj = (before[0] + price[0], before[1] + price[1])
                other = new.get(nxt)
                if other and other[0] < obj:
                    continue
                if other and other[0] == obj:
                    totals = other[2]
                    for k, v in tally.items():
                        totals[k] = totals.get(k, 0) + v
                    n = other[1] + ways
                else:
                    n, totals = ways, tally.copy()
                for k in affected:
                    totals[k] = totals.get(k, 0) + ways
                new[nxt] = (obj, n, totals)
        states = new
    answer = states.get((0,) * len(rows))
    if answer is None:
        return None
    objective, count, tally = answer
    return summarize(request, objective, den, count, tally)


def solve(request, independent=False):
    method = column_oracle if independent else optimal_tables
    return {"appeals": {a["id"]: method(request, a["fix"]) for a in request["appeals"]}}


def shortcut(request):
    result = solve(request)
    for answer in result["appeals"].values():
        if answer:
            # A mandatory-change oracle discards partially supported changes.
            counts = answer["changed_in"]
            for k in counts:
                if counts[k] < answer["tables"]:
                    counts[k] = 0
    return result
