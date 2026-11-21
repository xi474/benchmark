from itertools import combinations


def _solve(cpp, cpy):
    """Solve CPP * b = CPy for a small symmetric positive-definite matrix."""
    n = len(cpp)
    if n == 0:
        return []
    # Gaussian elimination with partial pivoting on a copy.
    a = [row[:] for row in cpp]
    b = list(cpy)
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-15:
            raise ValueError("singular parent covariance")
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            b[col], b[pivot] = b[pivot], b[col]
        pv = a[col][col]
        for r in range(col + 1, n):
            factor = a[r][col] / pv
            for c in range(col, n):
                a[r][c] -= factor * a[col][c]
            b[r] -= factor * b[col]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i]
        for j in range(i + 1, n):
            s -= a[i][j] * x[j]
        x[i] = s / a[i][i]
    return x


def compute(payload):
    """为每个节点及其容许的父集合计算未舍入回归系数。"""
    nodes = payload["nodes"]
    covariance = payload["covariance"]
    allowed = payload["allowed"]
    root = payload["root"]
    max_parents = payload.get("max_parents", len(nodes))

    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]

    # Candidate parents per node: allowed edges into the node, excluding
    # self-loops and edges into the root (root has no incoming edges).
    candidates = [[] for _ in nodes]
    for parent_name, child_name in allowed:
        p = index[parent_name]
        c = index[child_name]
        if c != root_idx and p != c:
            candidates[c].append(p)
    for c in range(len(nodes)):
        candidates[c] = sorted(set(candidates[c]))

    result = []
    for c in range(len(nodes)):
        table = {}
        cands = candidates[c]
        # Empty parent set always admissible.
        table[""] = []
        for size in range(1, min(max_parents, len(cands)) + 1):
            for combo in combinations(cands, size):
                parents = list(combo)
                cpp = [[covariance[p][q] for q in parents] for p in parents]
                cpy = [covariance[p][c] for p in parents]
                coeffs = _solve(cpp, cpy)
                key = ",".join(str(p) for p in parents)
                table[key] = coeffs
        result.append(table)

    return result
