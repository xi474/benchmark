"""Combine the two component JSON values under the business contract in TASK.md."""


def _median_score(a, b, c, k):
    median = sorted((a, b, c))[1]
    if median == k - 1:
        return 1
    if median == 0:
        return -1
    return 0


def _snapshot_result(snap, left, right):
    """left = [compatible, ac_quota_rowmajor]; right = per-b candidate layers."""
    ab = snap["ab"]
    bc = snap["bc"]
    ac = snap["ac"]
    forbidden = snap.get("forbidden", [])
    k = len(ab)

    compatible, ac_quota = left
    if not compatible:
        return None

    # right[b] is a list of candidate layers for that b.
    # Each candidate is [row-major count vector (a,c), median net score].
    # A full table is a choice of one candidate per b such that the ac totals
    # match the ac quota exactly.
    per_b = right
    n_b = len(per_b)

    # Enumerate all combinations of candidate layers across b.
    # Total people <= 40, k <= 4, so this is small.
    tables = []
    # Use iterative product over candidate indices.
    import itertools

    # Build list of candidate index lists per b.
    idx_lists = [list(range(len(per_b[b]))) for b in range(n_b)]

    for combo in itertools.product(*idx_lists):
        # Sum ac counts across chosen layers.
        ac_sum = [0] * (k * k)
        net = 0
        for b in range(n_b):
            vec, score = per_b[b][combo[b]]
            net += score
            for i in range(k * k):
                ac_sum[i] += vec[i]
        if ac_sum != ac_quota:
            continue
        # Build the full 3D table X[a][b][c].
        X = [[[0] * k for _ in range(k)] for _ in range(k)]
        for b in range(n_b):
            vec, _ = per_b[b][combo[b]]
            for a in range(k):
                for c in range(k):
                    X[a][b][c] = vec[a * k + c]
        tables.append((net, X))

    if not tables:
        return None

    # tables count
    tables_count = len(tables)

    # spectrum: net -> count, sorted ascending by net
    from collections import Counter
    net_counter = Counter(net for net, _ in tables)
    spectrum = [[net, net_counter[net]] for net in sorted(net_counter)]

    # guaranteed: cells with min count > 0 across all tables
    guaranteed = []
    for a in range(k):
        for b in range(k):
            for c in range(k):
                mn = min(X[a][b][c] for _, X in tables)
                if mn > 0:
                    guaranteed.append([a, b, c, mn])

    # witness: among tables with minimum net, lexicographically smallest
    # full (a,b,c) count vector (including zeros), output only nonzero cells.
    min_net = min(net for net, _ in tables)
    min_tables = [X for net, X in tables if net == min_net]

    def full_vector(X):
        return [X[a][b][c] for a in range(k) for b in range(k) for c in range(k)]

    witness_X = min(min_tables, key=full_vector)
    witness = []
    for a in range(k):
        for b in range(k):
            for c in range(k):
                v = witness_X[a][b][c]
                if v > 0:
                    witness.append([a, b, c, v])

    return {
        "tables": tables_count,
        "spectrum": spectrum,
        "guaranteed": guaranteed,
        "witness": witness,
    }


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    snapshots = payload["snapshots"]
    out = []
    for i, snap in enumerate(snapshots):
        out.append(_snapshot_result(snap, left[i], right[i]))
    return out
