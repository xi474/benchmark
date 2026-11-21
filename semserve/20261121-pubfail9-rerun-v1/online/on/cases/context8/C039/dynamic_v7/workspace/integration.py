"""C039 integration: select the prior-constrained causal DAG and compute do-intervention means."""

from itertools import combinations


def _residual_variance(covariance, child, parents):
    """Cyy - CyP * CPP^-1 * CPy for the given parent set (indices)."""
    if not parents:
        return covariance[child][child]
    n = len(parents)
    cpp = [[covariance[a][b] for b in parents] for a in parents]
    cpy = [covariance[p][child] for p in parents]
    # Solve CPP * x = CPy via Gaussian elimination with partial pivoting.
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
    x = [a[i][n] for i in range(n)]
    return covariance[child][child] - sum(x[i] * cpy[i] for i in range(n))


def _coefficients(covariance, child, parents):
    """Regression coefficients for child on parents (indices), in parent order."""
    if not parents:
        return []
    n = len(parents)
    cpp = [[covariance[a][b] for b in parents] for a in parents]
    cpy = [covariance[p][child] for p in parents]
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


def _is_dag(edges, n):
    """True if the directed graph on n nodes has no cycle."""
    adj = [[] for _ in range(n)]
    for p, c in edges:
        adj[p].append(c)
    state = [0] * n  # 0 unvisited, 1 visiting, 2 done

    def dfs(u):
        state[u] = 1
        for v in adj[u]:
            if state[v] == 1:
                return False
            if state[v] == 0 and not dfs(v):
                return False
        state[u] = 2
        return True

    for u in range(n):
        if state[u] == 0 and not dfs(u):
            return False
    return True


def combine(payload, left, right):
    """left: admissible edge index pairs; right: per-node regression tables."""
    nodes = payload["nodes"]
    covariance = payload["covariance"]
    mean = payload["mean"]
    sample_size = payload["sample_size"]
    root = payload["root"]
    edge_count = payload["edge_count"]
    max_parents = payload["max_parents"]
    intervention = payload["intervention"]

    n = len(nodes)
    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]

    admissible = [tuple(e) for e in left]

    # Build parent options per node from admissible edges.
    parents_of = [[] for _ in range(n)]
    for p, c in admissible:
        parents_of[c].append(p)
    for lst in parents_of:
        lst.sort()

    # Enumerate all parent-set combinations respecting max_parents and edge_count.
    # Each node chooses a parent subset; total edges must equal edge_count.
    # Root has no parents (admissible already excludes edges into root).
    best_score = None
    best_edges = None

    # Generate candidate parent sets per node.
    options = []
    for c in range(n):
        opts = [()]
        ps = parents_of[c]
        for size in range(1, min(max_parents, len(ps)) + 1):
            for combo in combinations(ps, size):
                opts.append(combo)
        options.append(opts)

    # Recursive search over nodes.
    def search(node_idx, chosen, total_edges):
        nonlocal best_score, best_edges
        if node_idx == n:
            if total_edges != edge_count:
                return
            edges = []
            for c in range(n):
                for p in chosen[c]:
                    edges.append((p, c))
            if not _is_dag(edges, n):
                return
            # Compute score.
            score = 0.0
            for c in range(n):
                rv = _residual_variance(covariance, c, list(chosen[c]))
                score += sample_size * _ln(rv) + len(chosen[c]) * _ln(sample_size)
            score = round(score, 9)
            key = tuple(sorted(edges))
            if best_score is None or score < best_score or (score == best_score and key < best_edges_key):
                best_score = score
                best_edges = edges
                best_edges_key = key
            return
        for combo in options[node_idx]:
            if total_edges + len(combo) > edge_count:
                continue
            chosen[node_idx] = combo
            search(node_idx + 1, chosen, total_edges + len(combo))

    best_edges_key = None
    chosen = [()] * n
    search(0, chosen, 0)

    if best_edges is None:
        return {"feasible": False}

    # Sort edges lexicographically.
    edges = sorted(best_edges)

    # Coefficients for each edge (parent -> child).
    coeffs = []
    for p, c in edges:
        parents = sorted([pp for pp, cc in edges if cc == c])
        coef = _coefficients(covariance, c, parents)
        pos = parents.index(p)
        coeffs.append([p, c, coef[pos]])

    # Intervened edges: all edges into the intervention node and its descendants.
    iv_node = index[intervention["node"]]
    desc = set()
    stack = [iv_node]
    while stack:
        u = stack.pop()
        if u in desc:
            continue
        desc.add(u)
        for p, c in edges:
            if p == u:
                stack.append(c)
    intervened_edges = sorted([(p, c) for p, c in edges if c in desc])

    # Compute intervention means.
    # Intervened node is set to value; its incoming edges are cut.
    # Other nodes keep slopes and intercepts determined by observed mean.
    # Process nodes in topological order of the intervened graph.
    value = intervention["value"]
    result_mean = [None] * n
    result_mean[iv_node] = value

    # Build intervened graph: edges minus intervened edges.
    remaining = [e for e in edges if e not in intervened_edges]
    adj = [[] for _ in range(n)]
    for p, c in remaining:
        adj[p].append(c)
    # Topological order.
    indeg = [0] * n
    for p, c in remaining:
        indeg[c] += 1
    from collections import deque
    q = deque([u for u in range(n) if indeg[u] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    for c in order:
        if c == iv_node:
            continue
        parents = sorted([p for p, cc in remaining if cc == c])
        coef = _coefficients(covariance, c, parents)
        # intercept = mean[c] - sum(coef_i * mean[parent_i])
        intercept = mean[c] - sum(coef[i] * mean[parents[i]] for i in range(len(parents)))
        val = intercept + sum(coef[i] * result_mean[parents[i]] for i in range(len(parents)))
        result_mean[c] = val

    # Round outputs.
    score_rounded = round(best_score, 6)
    edges_out = [[nodes[p], nodes[c]] for p, c in edges]
    coeffs_out = [[nodes[p], nodes[c], round(v, 6)] for p, c, v in coeffs]
    intervened_out = [[nodes[p], nodes[c]] for p, c in intervened_edges]
    mean_out = [round(v, 6) for v in result_mean]

    return {
        "feasible": True,
        "edges": edges_out,
        "score": score_rounded,
        "coefficients": coeffs_out,
        "intervened_edges": intervened_out,
        "mean": mean_out,
    }


def _ln(x):
    import math
    return math.log(x)
