import json
import math
from itertools import combinations
from pathlib import Path


def load_payload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _round6(x):
    return round(x, 6)


def _score_dag(nodes, parents, covariance, mean, sample_size):
    # parents: dict node -> list of parent indices
    n = len(nodes)
    total = 0.0
    for i in range(n):
        ps = parents[i]
        k = len(ps)
        if k == 0:
            var = covariance[i][i]
        else:
            # Cyy - CyP * CPP^-1 * CPy
            CPP = [[covariance[a][b] for b in ps] for a in ps]
            CyP = [covariance[i][b] for b in ps]
            CPy = [covariance[a][i] for a in ps]
            # solve CPP * x = CPy
            x = _solve(CPP, CPy)
            var = covariance[i][i] - sum(CyP[j] * x[j] for j in range(k))
        total += sample_size * math.log(var) + k * math.log(sample_size)
    return total


def _solve(A, b):
    # Gaussian elimination for small SPD matrix
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        # pivot
        piv = col
        for r in range(col, n):
            if abs(M[r][col]) > abs(M[piv][col]):
                piv = r
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(col + 1, n):
            f = M[r][col] / pv
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = M[i][n]
        for j in range(i + 1, n):
            s -= M[i][j] * x[j]
        x[i] = s / M[i][i]
    return x


def _coefficients(nodes, parents, covariance):
    # returns dict (parent_idx, child_idx) -> slope
    coef = {}
    n = len(nodes)
    for i in range(n):
        ps = parents[i]
        k = len(ps)
        if k == 0:
            continue
        CPP = [[covariance[a][b] for b in ps] for a in ps]
        CPy = [covariance[a][i] for a in ps]
        x = _solve(CPP, CPy)
        for j, p in enumerate(ps):
            coef[(p, i)] = x[j]
    return coef


def _topo_order(nodes, parents):
    n = len(nodes)
    indeg = [0] * n
    children = [[] for _ in range(n)]
    for i in range(n):
        for p in parents[i]:
            indeg[i] += 1
            children[p].append(i)
    order = []
    q = [i for i in range(n) if indeg[i] == 0]
    while q:
        i = q.pop(0)
        order.append(i)
        for c in children[i]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    return order if len(order) == n else None


def transform(payload):
    nodes = list(payload["nodes"])
    covariance = payload["covariance"]
    mean = payload["mean"]
    sample_size = payload["sample_size"]
    allowed = payload["allowed"]
    root = payload["root"]
    edge_count = payload["edge_count"]
    max_parents = payload["max_parents"]
    intervention = payload["intervention"]

    n = len(nodes)
    idx = {name: i for i, name in enumerate(nodes)}
    root_idx = idx[root]

    # allowed edges as (parent_idx, child_idx)
    allowed_edges = []
    for p, c in allowed:
        pi, ci = idx[p], idx[c]
        if pi != root_idx and ci != root_idx:
            # root has no incoming edges; root can have outgoing
            pass
        allowed_edges.append((pi, ci))

    # root has no incoming edges -> filter out edges into root
    allowed_edges = [(p, c) for p, c in allowed_edges if c != root_idx]

    # enumerate all subsets of allowed edges of size edge_count
    best = None
    best_score = None
    best_edges = None

    for combo in combinations(allowed_edges, edge_count):
        # build parents
        parents = [[] for _ in range(n)]
        ok = True
        for p, c in combo:
            parents[c].append(p)
            if len(parents[c]) > max_parents:
                ok = False
                break
        if not ok:
            continue
        # check acyclic
        if _topo_order(nodes, parents) is None:
            continue
        score = _score_dag(nodes, parents, covariance, mean, sample_size)
        rscore = round(score, 9)
        if best_score is None or rscore < best_score or (rscore == best_score and _edge_key(combo) < _edge_key(best_edges)):
            best_score = rscore
            best = parents
            best_edges = combo

    if best is None:
        return {"feasible": False}

    # build edges list sorted
    edges = sorted([[nodes[p], nodes[c]] for p, c in best_edges])

    coef = _coefficients(nodes, best, covariance)
    coefficients = sorted([[nodes[p], nodes[c], _round6(coef[(p, c)])] for p, c in best_edges])

    # intervention
    iv_node = intervention["node"]
    iv_value = intervention["value"]
    iv_idx = idx[iv_node]

    # intervened edges: all edges into iv_node
    intervened_edges = sorted([[nodes[p], nodes[c]] for p, c in best_edges if c == iv_idx])

    # compute expected means after intervention
    # topological order
    order = _topo_order(nodes, best)
    # compute means
    result_mean = [0.0] * n
    for i in order:
        if i == iv_idx:
            result_mean[i] = iv_value
            continue
        ps = best[i]
        if not ps:
            result_mean[i] = mean[i]
        else:
            # intercept = mean[i] - sum(slope * mean[parent])
            val = mean[i]
            for p in ps:
                val -= coef[(p, i)] * mean[p]
            # add slopes * result_mean[parent]
            for p in ps:
                val += coef[(p, i)] * result_mean[p]
            result_mean[i] = val

    mean_out = [_round6(result_mean[i]) for i in range(n)]

    return {
        "feasible": True,
        "edges": edges,
        "score": _round6(best_score),
        "coefficients": coefficients,
        "intervened_edges": intervened_edges,
        "mean": mean_out,
    }


def _edge_key(combo):
    return sorted(combo)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
