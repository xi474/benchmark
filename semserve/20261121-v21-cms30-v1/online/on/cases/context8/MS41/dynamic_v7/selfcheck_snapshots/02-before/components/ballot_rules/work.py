from math import gcd


def _simplify(num, den):
    if num == 0:
        return [0, 1]
    g = gcd(num, den)
    return [num // g, den // g]


def _decide(counts, votes):
    """Return the winning answer index if the winner is already determined,
    otherwise None. The current leader is the answer with the most votes,
    ties broken by the earliest position in `answers`. The leader is
    guaranteed to win when, for every competitor, giving that competitor all
    remaining votes still leaves the leader as the final winner (ties broken
    by answers order)."""
    n = len(counts)
    total = sum(counts)
    remaining = votes - total
    leader = 0
    for i in range(1, n):
        if counts[i] > counts[leader]:
            leader = i
    for c in range(n):
        if c == leader:
            continue
        if counts[leader] > counts[c] + remaining:
            continue
        if counts[leader] == counts[c] + remaining and leader < c:
            continue
        return None
    return leader


def compute(payload):
    """输出 [先验映射,方法提前决胜表]。先验为最简分数。每种方法列出从零票起
    可达的计数状态（键为逗号分隔的答案票数）；值是已经胜出的答案下标或 null。
    决胜后不扩展。"""
    answers = payload["answers"]
    profiles = payload["profiles"]
    methods = payload["methods"]
    n = len(answers)

    total_weight = sum(profiles.values())
    prior = {name: _simplify(weight, total_weight) for name, weight in profiles.items()}

    table = {}
    for method in methods:
        votes = method["votes"]
        start = tuple([0] * n)
        visited = {start}
        queue = [start]
        mtable = {}
        while queue:
            state = queue.pop(0)
            decision = _decide(state, votes)
            mtable[",".join(str(x) for x in state)] = decision
            if decision is None and sum(state) < votes:
                for i in range(n):
                    child = list(state)
                    child[i] += 1
                    child = tuple(child)
                    if child not in visited:
                        visited.add(child)
                        queue.append(child)
        table[method["id"]] = mtable

    return [prior, table]
