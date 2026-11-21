from itertools import combinations


def _solve(cpp, cpy):
    """Solve cpp * x = cpy via Gaussian elimination with partial pivoting."""
    n = len(cpp)
    a = [list(row) + [cpy[i]] for i, row in enumerate(cpp)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-15:
            raise ValueError("singular parent covariance")
        a[col], a[pivot] = a[pivot], a[col]
        pv = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= pv
        for r in range(n):
            if r != col and a[r][col] != 0.0:
                factor = a[r][col]
                for j in range(col, n + 1):
                    a[r][j] -= factor * a[col][j]
    return [a[i][n] for i in range(n)]


def compute(payload):
    nodes = payload["nodes"]
    covariance = payload["covariance"]
    allowed = payload["allowed"]
    root = payload["root"]
    max_parents = payload["max_parents"]

    n = len(nodes)
    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]

    # Admissible parents for each node: allowed edges into it, excluding root.
    parents_of = [[] for _ in range(n)]
    for p_name, c_name in allowed:
        p = index[p_name]
        c = index[c_name]
        if c != root_idx:
            parents_of[c].append(p)
    for lst in parents_of:
        lst.sort()

    result = []
    for c in range(n):
        table = {}
        parents = parents_of[c]
        # Empty parent set.
        table[""] = []
        for size in range(1, max_parents + 1):
            for combo in combinations(parents, size):
                key = ",".join(str(p) for p in combo)
                cpp = [[covariance[a][b] for b in combo] for a in combo]
                cpy = [covariance[p][c] for p in combo]
                table[key] = _solve(cpp, cpy)
        result.append(table)
    return result
