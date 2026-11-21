def _median_score(a, b, c, k):
    """Net score of one customer with ratings (a, b, c)."""
    median = sorted((a, b, c))[1]
    if median == k - 1:
        return 1
    if median == 0:
        return -1
    return 0


def _enumerate_layers(row_sums, col_sums, upper, k):
    """All non-negative k x k matrices with given row/col sums and cell caps."""
    results = []
    mat = [[0] * k for _ in range(k)]
    rem_col = list(col_sums)

    def rec_row(a):
        if a == k:
            if all(rem_col[c] == 0 for c in range(k)):
                results.append([mat[r][c] for r in range(k) for c in range(k)])
            return

        def rec_col(c, remaining):
            if c == k - 1:
                if remaining <= upper[a][c] and remaining <= rem_col[c]:
                    mat[a][c] = remaining
                    rem_col[c] -= remaining
                    rec_row(a + 1)
                    rem_col[c] += remaining
                    mat[a][c] = 0
                return
            maxv = min(remaining, upper[a][c], rem_col[c])
            for v in range(maxv + 1):
                mat[a][c] = v
                rem_col[c] -= v
                rec_col(c + 1, remaining - v)
                rem_col[c] += v
                mat[a][c] = 0

        rec_col(0, row_sums[a])

    rec_row(0)
    return results


def _snapshot_layers(ab, bc, ac, forbidden, k):
    forbidden_set = set(tuple(t) for t in forbidden)
    per_b = []
    for b in range(k):
        row_sums = [ab[a][b] for a in range(k)]
        col_sums = [bc[b][c] for c in range(k)]
        upper = [[0 if (a, b, c) in forbidden_set else ac[a][c]
                  for c in range(k)] for a in range(k)]
        candidates = []
        for vec in _enumerate_layers(row_sums, col_sums, upper, k):
            score = 0
            for a in range(k):
                for c in range(k):
                    v = vec[a * k + c]
                    if v:
                        score += v * _median_score(a, b, c, k)
            candidates.append([vec, score])
        candidates.sort(key=lambda item: item[0])
        per_b.append(candidates)
    return per_b


def compute(payload):
    """为每个快照按 b 生成候选层数组。"""
    snapshots = payload["snapshots"]
    result = []
    for snap in snapshots:
        ab = snap["ab"]
        bc = snap["bc"]
        ac = snap["ac"]
        forbidden = snap.get("forbidden", [])
        k = len(ab)
        result.append(_snapshot_layers(ab, bc, ac, forbidden, k))
    return result
