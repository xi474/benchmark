import json
from itertools import combinations


def _round9(x):
    return round(x, 9)


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    nodes = payload["nodes"]
    n = len(nodes)
    covariance = payload["covariance"]
    mean = payload["mean"]
    sample_size = payload["sample_size"]
    allowed = payload["allowed"]
    root = payload["root"]
    edge_count = payload["edge_count"]
    max_parents = payload["max_parents"]
    intervention = payload.get("intervention")

    index = {name: i for i, name in enumerate(nodes)}
    root_idx = index[root]

    # left: admissible edges (node-index pairs, allowed order, no edge into root)
    admissible = [tuple(e) for e in left]

    # right: per-node regression tables keyed by comma-separated ascending parent indices
    regressions = right

    # Build candidate parent sets per node from admissible edges.
    cand_parents = [set() for _ in range(n)]
    for p, c in admissible:
        cand_parents[c].add(p)
    cand_parents = [sorted(s) for s in cand_parents]

    # Precompute residual variance for each node and parent set.
    # residual variance = Cyy - CyP * CPP^-1 * CPy
    def residual_var(c, parents):
        if not parents:
            return covariance[c][c]
        cpp = [[covariance[p][q] for q in parents] for p in parents]
        cpy = [covariance[p][c] for p in parents]
        coeffs = _solve(cpp, cpy)
        cyy = covariance[c][c]
        s = cyy - sum(coeffs[i] * cpy[i] for i in range(len(parents)))
        return s

    # Enumerate all valid DAGs with exactly edge_count edges.
    # Each node's parents must be a subset of cand_parents[c], size <= max_parents.
    # Root has no parents (already excluded by admissible edges).
    # Acyclicity: since we only need to check, we can use topological ordering via
    # the fact that a DAG has a topological order. We'll enumerate parent-set choices
    # and check acyclicity.

    best = None  # (score9, edge_list_sorted, edges, coeffs_by_edge)

    # Enumerate parent sets for each node (excluding root which has none).
    # Use recursion over nodes.
    def enumerate_node(node_idx, chosen_parents, edges_so_far):
        nonlocal best
        if node_idx == n:
            if len(edges_so_far) != edge_count:
                return
            # check acyclicity
            if not _is_acyclic(n, edges_so_far):
                return
            # compute score
            total = 0.0
            for c in range(n):
                parents = chosen_parents[c]
                rv = residual_var(c, parents)
                total += sample_size * math.log(rv) + len(parents) * math.log(sample_size)
            score9 = _round9(total)
            edge_list = sorted(edges_so_far)
            key = (score9, edge_list)
            if best is None or key < best[0]:
                best = (key, edges_so_far, chosen_parents)
            return
        if node_idx == root_idx:
            enumerate_node(node_idx + 1, chosen_parents, edges_so_far)
            return
        cands = cand_parents[node_idx]
        # generate all subsets of cands with size <= max_parents
        for size in range(0, min(max_parents, len(cands)) + 1):
            for combo in combinations(cands, size):
                new_parents = chosen_parents[:]
                new_parents[node_idx] = list(combo)
                new_edges = edges_so_far + [(p, node_idx) for p in combo]
                enumerate_node(node_idx + 1, new_parents, new_edges)

    import math
    chosen_parents = [[] for _ in range(n)]
    enumerate_node(0, chosen_parents, [])

    if best is None:
        return {"feasible": False}

    (score9, edge_list), edges, parents = best

    # Build coefficients for each edge (parent -> child) using regression table.
    coeffs = []
    for c in range(n):
        ps = parents[c]
        if not ps:
            continue
        key = ",".join(str(p) for p in sorted(ps))
        table = regressions[c]
        vals = table[key]
        for i, p in enumerate(sorted(ps)):
            coeffs.append([p, c, vals[i]])

    # Sort edges and coefficients by (parent, child) lexicographic on node names.
    edges_sorted = sorted(edges, key=lambda e: (e[0], e[1]))
    coeffs_sorted = sorted(coeffs, key=lambda e: (e[0], e[1]))

    edges_out = [[nodes[p], nodes[c]] for p, c in edges_sorted]
    coeffs_out = [[nodes[p], nodes[c], round(v, 6)] for p, c, v in coeffs_sorted]

    score_out = round(score9, 6)

    # Intervention
    intervened_edges = []
    mean_out = list(mean)
    if intervention is not None:
        iv_node = intervention["node"]
        iv_value = intervention["value"]
        iv_idx = index[iv_node]
        # Cut all incoming edges to iv_node.
        intervened_edges = [[nodes[p], nodes[c]] for p, c in edges_sorted if c == iv_idx]
        intervened_edges = sorted(intervened_edges, key=lambda e: (e[0], e[1]))
        # The intervened node's outgoing edges are also cut (do-intervention severs
        # all edges incident to the node).
        # Compute expected means via topological order.
        # For each node, mean = intercept + sum(coeff * parent_mean)
        # intercept = mean[c] - sum(coeff * mean[p]) using observed means.
        # For intervened node, mean = value.
        # Process nodes in topological order.
        order = _topo_order(n, edges_sorted)
        node_mean = [None] * n
        for c in order:
            if c == iv_idx:
                node_mean[c] = iv_value
                continue
            ps = parents[c]
            if not ps:
                node_mean[c] = mean[c]
                continue
            key = ",".join(str(p) for p in sorted(ps))
            vals = regressions[c][key]
            # intercept = mean[c] - sum(coeff * mean[p])
            intercept = mean[c]
            for i, p in enumerate(sorted(ps)):
                intercept -= vals[i] * mean[p]
            m = intercept
            for i, p in enumerate(sorted(ps)):
                m += vals[i] * node_mean[p]
            node_mean[c] = m
        mean_out = [round(node_mean[i], 6) for i in range(n)]

    return {
        "feasible": True,
        "edges": edges_out,
        "score": score_out,
        "coefficients": coeffs_out,
        "intervened_edges": intervened_edges,
        "mean": mean_out,
    }


def _solve(cpp, cpy):
    """Solve CPP * b = CPy via Gaussian elimination with partial pivoting."""
    n = len(cpp)
    if n == 0:
        return []
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


def _is_acyclic(n, edges):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for p, c in edges:
        adj[p].append(c)
        indeg[c] += 1
    from collections import deque
    q = deque([i for i in range(n) if indeg[i] == 0])
    seen = 0
    while q:
        u = q.popleft()
        seen += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return seen == n


def _topo_order(n, edges):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for p, c in edges:
        adj[p].append(c)
        indeg[c] += 1
    from collections import deque
    q = deque([i for i in range(n) if indeg[i] == 0])
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return order
