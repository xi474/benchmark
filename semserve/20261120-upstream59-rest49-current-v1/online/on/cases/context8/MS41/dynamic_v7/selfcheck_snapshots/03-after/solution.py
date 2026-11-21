from fractions import Fraction
from pathlib import Path
import json
from functools import lru_cache


def _simplify(f):
    if f.denominator < 0:
        f = -f
    return [f.numerator, f.denominator]


def _solve(A, b):
    """Solve A x = b over Fractions. A is n x n, b length n.
    Returns solution list or None if inconsistent."""
    n = len(A)
    aug = [A[i][:] + [b[i]] for i in range(n)]
    row = 0
    pivot_cols = []
    for col in range(n):
        piv = None
        for r in range(row, n):
            if aug[r][col] != 0:
                piv = r
                break
        if piv is None:
            continue
        aug[row], aug[piv] = aug[piv], aug[row]
        pv = aug[row][col]
        for c in range(col, n + 1):
            aug[row][c] /= pv
        for r in range(n):
            if r != row and aug[r][col] != 0:
                f = aug[r][col]
                for c in range(col, n + 1):
                    aug[r][c] -= f * aug[row][c]
        pivot_cols.append(col)
        row += 1
    for r in range(row, n):
        if aug[r][n] != 0:
            return None
    sol = [Fraction(0) for _ in range(n)]
    for r, col in enumerate(pivot_cols):
        sol[col] = aug[r][n]
    return sol


def _version_stats(graph, start, answers):
    """For one version graph, compute per-answer:
       p[a] = P(vote yields a), e[a] = E[cost * 1{yields a}], u = P(unresolved).
    Returns (p dict, e dict, u Fraction)."""
    states = list(graph.keys())
    idx = {s: i for i, s in enumerate(states)}
    n = len(states)
    edges_info = []
    for s in states:
        total = sum(w for (t, w, c) in graph[s])
        edges_info.append((total, graph[s]))

    A = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        A[i][i] = Fraction(1)
        total, edges = edges_info[i]
        for (t, w, c) in edges:
            p = Fraction(w, total)
            if t in idx:
                A[i][idx[t]] -= p

    num_answers = len(answers)
    # RHS for x[a]
    rhs_x = [[Fraction(0) for _ in range(num_answers)] for _ in range(n)]
    for i in range(n):
        total, edges = edges_info[i]
        for (t, w, c) in edges:
            p = Fraction(w, total)
            if t in answers:
                a = answers.index(t)
                rhs_x[i][a] += p

    x_sol = []
    for a in range(num_answers):
        b = [rhs_x[i][a] for i in range(n)]
        x_sol.append(_solve(A, b))

    y_sol = []
    for a in range(num_answers):
        d = [Fraction(0) for _ in range(n)]
        for i in range(n):
            total, edges = edges_info[i]
            for (t, w, c) in edges:
                p = Fraction(w, total)
                if t in idx:
                    d[i] += p * c * x_sol[a][idx[t]]
                elif t == answers[a]:
                    d[i] += p * c
        y_sol.append(_solve(A, d))

    si = idx[start]
    p = {}
    e = {}
    for a in range(num_answers):
        p[answers[a]] = x_sol[a][si]
        e[answers[a]] = y_sol[a][si]
    u = Fraction(1) - sum(p.values())
    return p, e, u


def transform(payload):
    answers = payload['answers']
    correct = payload['correct']
    profiles = payload['profiles']
    methods = payload['methods']

    results = []
    for method in methods:
        votes = method['votes']
        start = method['start']
        graphs = method['graphs']

        version_data = {}
        for version, graph in graphs.items():
            version_data[version] = _version_stats(graph, start, answers)

        total_weight = sum(profiles[v] for v in graphs)
        P_vote = {a: Fraction(0) for a in answers}
        E_vote = {a: Fraction(0) for a in answers}
        U_vote = Fraction(0)
        for v in graphs:
            w = Fraction(profiles[v], total_weight)
            p, e, u = version_data[v]
            for a in answers:
                P_vote[a] += w * p[a]
                E_vote[a] += w * e[a]
            U_vote += w * u

        @lru_cache(maxsize=None)
        def dp(counts, launched):
            if launched > 0:
                maxc = max(counts)
                leader = None
                for a in range(len(answers)):
                    if counts[a] == maxc:
                        leader = a
                        break
                remaining = votes - launched
                can_declare = True
                for b in range(len(answers)):
                    if b == leader:
                        continue
                    if b < leader:
                        if counts[b] + remaining >= counts[leader]:
                            can_declare = False
                            break
                    else:
                        if counts[b] + remaining > counts[leader]:
                            can_declare = False
                            break
                if can_declare or launched == votes:
                    prob = {answers[a]: (Fraction(1) if a == leader else Fraction(0))
                            for a in range(len(answers))}
                    return (prob, Fraction(0), Fraction(launched),
                            {answers[a]: Fraction(0) for a in range(len(answers))})

            prob = {a: Fraction(0) for a in answers}
            unres = Fraction(0)
            launches = Fraction(0)
            cost = {a: Fraction(0) for a in answers}

            unres += U_vote
            launches += U_vote

            for b in range(len(answers)):
                pb = P_vote[answers[b]]
                if pb == 0:
                    continue
                new_counts = list(counts)
                new_counts[b] += 1
                new_counts = tuple(new_counts)
                prob2, unres2, launches2, cost2 = dp(new_counts, launched + 1)
                for a in answers:
                    prob[a] += pb * prob2[a]
                    cost[a] += E_vote[answers[b]] * prob2[a] + pb * cost2[a]
                unres += pb * unres2
                launches += pb * launches2

            return (prob, unres, launches, cost)

        prob, unres, launches, cost = dp(tuple([0] * len(answers)), 0)

        if prob[correct] > 0:
            cost_if_correct = cost[correct] / prob[correct]
        else:
            cost_if_correct = None

        prob_list = [_simplify(prob[a]) for a in answers]
        unres_list = _simplify(unres)
        launches_list = _simplify(launches)
        cost_list = None if cost_if_correct is None else _simplify(cost_if_correct)

        results.append({
            'id': method['id'],
            'prob': prob_list,
            'unresolved': unres_list,
            'launches': launches_list,
            'cost_if_correct': cost_list,
        })

    ci = answers.index(correct)
    results.sort(key=lambda r: (-Fraction(r['prob'][ci][0], r['prob'][ci][1]), r['id']))

    return results


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
