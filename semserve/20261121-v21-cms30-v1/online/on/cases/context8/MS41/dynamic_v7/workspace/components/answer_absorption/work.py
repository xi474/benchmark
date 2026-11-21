from collections import deque
from fractions import Fraction


def _reduce(f):
    return [f.numerator, f.denominator]


def _solve(A, b):
    """Solve A x = b over rationals via Gaussian elimination. A is n x n, b length n."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = None
        for r in range(col, n):
            if M[r][col] != 0:
                piv = r
                break
        if piv is None:
            raise ValueError("singular system")
        if piv != col:
            M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        M[col] = [x / pv for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                factor = M[r][col]
                M[r] = [M[r][c] - factor * M[col][c] for c in range(n + 1)]
    return [M[i][n] for i in range(n)]


def compute(payload):
    """按 method ID、profile 名输出 [各答案吸收概率,各答案加权成本质量]。

    每个向量元素为约分的 [分子,分母]，保留 answers 顺序。
    """
    answers = payload["answers"]
    methods = payload["methods"]
    ans_index = {a: i for i, a in enumerate(answers)}
    n_ans = len(answers)

    result = {}
    for method in methods:
        mid = method["id"]
        start = method["start"]
        graphs = method["graphs"]
        method_result = {}
        for profile, graph in graphs.items():
            states = list(graph.keys())

            # Identify transient states: non-terminal states that can reach an answer.
            reverse = {}
            for s in states:
                for (t, w, c) in graph[s]:
                    reverse.setdefault(t, []).append(s)

            can_reach = set()
            dq = deque()
            for a in answers:
                for s in reverse.get(a, []):
                    if s not in can_reach:
                        can_reach.add(s)
                        dq.append(s)
            while dq:
                s = dq.popleft()
                for pred in reverse.get(s, []):
                    if pred not in can_reach:
                        can_reach.add(pred)
                        dq.append(pred)

            transient = [s for s in states if s in can_reach]
            idx = {s: i for i, s in enumerate(transient)}
            n = len(transient)

            start_idx = idx.get(start)

            if start_idx is None:
                # start never reaches an answer: zero absorption and zero cost mass.
                probs = [[0, 1] for _ in range(n_ans)]
                cost_mass = [[0, 1] for _ in range(n_ans)]
                method_result[profile] = [probs, cost_mass]
                continue

            # A = I - Q over transient states.
            A = [[Fraction(0) for _ in range(n)] for _ in range(n)]
            for i in range(n):
                A[i][i] = Fraction(1)

            b_p = [[Fraction(0) for _ in range(n)] for _ in range(n_ans)]
            b_c = [[Fraction(0) for _ in range(n)] for _ in range(n_ans)]

            for s in transient:
                si = idx[s]
                edges = graph[s]
                W = sum(w for (t, w, c) in edges)
                for (t, w, c) in edges:
                    frac = Fraction(w, W)
                    if t in ans_index:
                        ai = ans_index[t]
                        b_p[ai][si] += frac
                        b_c[ai][si] += frac * c
                    else:
                        # Non-terminal target: pay cost now regardless of final answer.
                        for ai in range(n_ans):
                            b_c[ai][si] += frac * c
                        if t in idx:
                            A[si][idx[t]] -= frac

            probs = []
            cost_mass = []
            for ai in range(n_ans):
                p = _solve(A, b_p[ai])
                c = _solve(A, b_c[ai])
                probs.append(_reduce(p[start_idx]))
                cost_mass.append(_reduce(c[start_idx]))

            method_result[profile] = [probs, cost_mass]

        result[mid] = method_result

    return result
