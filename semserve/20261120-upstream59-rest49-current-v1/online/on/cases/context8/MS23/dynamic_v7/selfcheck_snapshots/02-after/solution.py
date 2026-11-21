import json
from collections import Counter
from pathlib import Path


def _median_score(a, b, c, k):
    vals = sorted((a, b, c))
    med = vals[1]
    if med == k - 1:
        return 1
    if med == 0:
        return -1
    return 0


def _solve_snapshot(snap):
    ab = snap["ab"]
    bc = snap["bc"]
    ac = snap["ac"]
    k = len(ab)
    forbidden = set(tuple(t) for t in snap.get("forbidden", []))

    total_ab = sum(sum(row) for row in ab)
    total_bc = sum(sum(row) for row in bc)
    total_ac = sum(sum(row) for row in ac)
    if not (total_ab == total_bc == total_ac):
        return None

    cells = [(a, b, c) for a in range(k) for b in range(k) for c in range(k)]
    n = len(cells)
    allowed = [t not in forbidden for t in cells]

    # Running projection sums during search.
    ab_sum = [[0] * k for _ in range(k)]
    ac_sum = [[0] * k for _ in range(k)]
    bc_sum = [[0] * k for _ in range(k)]

    # Full 3D table being built.
    X = [[[0] * k for _ in range(k)] for _ in range(k)]

    tables = []

    def rec(idx, remaining):
        if idx == n:
            for a in range(k):
                for b in range(k):
                    if ab_sum[a][b] != ab[a][b]:
                        return
            for a in range(k):
                for c in range(k):
                    if ac_sum[a][c] != ac[a][c]:
                        return
            for b in range(k):
                for c in range(k):
                    if bc_sum[b][c] != bc[b][c]:
                        return
            tables.append([[row[:] for row in plane] for plane in X])
            return

        a, b, c = cells[idx]
        max_ab = ab[a][b] - ab_sum[a][b]
        max_ac = ac[a][c] - ac_sum[a][c]
        max_bc = bc[b][c] - bc_sum[b][c]
        cap = min(max_ab, max_ac, max_bc)
        if not allowed[idx]:
            cap = 0
        cap = min(cap, remaining)

        for v in range(cap + 1):
            X[a][b][c] = v
            ab_sum[a][b] += v
            ac_sum[a][c] += v
            bc_sum[b][c] += v
            rec(idx + 1, remaining - v)
            ab_sum[a][b] -= v
            ac_sum[a][c] -= v
            bc_sum[b][c] -= v
            X[a][b][c] = 0

    rec(0, total_ab)

    if not tables:
        return None

    results = []
    for X in tables:
        net = 0
        for a in range(k):
            for b in range(k):
                for c in range(k):
                    cnt = X[a][b][c]
                    if cnt:
                        net += cnt * _median_score(a, b, c, k)
        results.append((net, X))

    counts = Counter(net for net, _ in results)
    spectrum = [[net, counts[net]] for net in sorted(counts)]

    guaranteed = []
    for a in range(k):
        for b in range(k):
            for c in range(k):
                if (a, b, c) in forbidden:
                    continue
                mn = min(X[a][b][c] for _, X in results)
                if mn > 0:
                    guaranteed.append([a, b, c, mn])

    min_net = min(net for net, _ in results)
    candidates = [X for net, X in results if net == min_net]

    def flat(X):
        return tuple(X[a][b][c] for a in range(k) for b in range(k) for c in range(k))

    candidates.sort(key=flat)
    W = candidates[0]
    witness = []
    for a in range(k):
        for b in range(k):
            for c in range(k):
                if W[a][b][c] > 0:
                    witness.append([a, b, c, W[a][b][c]])

    return {
        "tables": len(tables),
        "spectrum": spectrum,
        "guaranteed": guaranteed,
        "witness": witness,
    }


def transform(payload):
    snapshots = payload["snapshots"]
    return [_solve_snapshot(s) for s in snapshots]


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return value
