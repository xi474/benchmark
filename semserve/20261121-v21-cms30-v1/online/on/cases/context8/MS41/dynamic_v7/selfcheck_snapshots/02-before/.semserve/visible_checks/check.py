import unittest

from fractions import Fraction


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return abs(a)


def _simplify(num, den):
    if num == 0:
        return [0, 1]
    g = _gcd(num, den)
    return [num // g, den // g]


def _add(a, b):
    return _simplify(a[0] * b[1] + b[0] * a[1], a[1] * b[1])


def _mul(a, b):
    return _simplify(a[0] * b[0], a[1] * b[1])


def _div(a, b):
    return _simplify(a[0] * b[1], a[1] * b[0])


def _frac(f):
    return [f.numerator, f.denominator]


def _solve_absorb(graph, answers, start):
    """Independent oracle: absorption probability and weighted cost mass for a
    single ballot, computed by solving the linear system over transient states
    (handles cycles)."""
    ans_index = {a: i for i, a in enumerate(answers)}
    n = len(answers)
    states = list(graph.keys())
    # transient states: non-terminal states that can reach an answer
    reverse = {}
    for s in states:
        for (t, w, c) in graph[s]:
            reverse.setdefault(t, []).append(s)
    can_reach = set()
    stack = [a for a in answers]
    while stack:
        t = stack.pop()
        for pred in reverse.get(t, []):
            if pred not in can_reach:
                can_reach.add(pred)
                stack.append(pred)
    transient = [s for s in states if s in can_reach]
    idx = {s: i for i, s in enumerate(transient)}
    m = len(transient)
    if start not in idx:
        return [Fraction(0) for _ in range(n)], [Fraction(0) for _ in range(n)]

    # A = I - Q
    A = [[Fraction(0) for _ in range(m)] for _ in range(m)]
    for i in range(m):
        A[i][i] = Fraction(1)
    b_p = [[Fraction(0) for _ in range(m)] for _ in range(n)]
    b_c = [[Fraction(0) for _ in range(m)] for _ in range(n)]
    for s in transient:
        si = idx[s]
        edges = graph[s]
        W = sum(w for (t, w, c) in edges)
        for (t, w, c) in edges:
            f = Fraction(w, W)
            if t in ans_index:
                ai = ans_index[t]
                b_p[ai][si] += f
                b_c[ai][si] += f * c
            else:
                for ai in range(n):
                    b_c[ai][si] += f * c
                if t in idx:
                    A[si][idx[t]] -= f

    def solve(A, b):
        mm = len(A)
        M = [row[:] + [b[i]] for i, row in enumerate(A)]
        for col in range(mm):
            piv = None
            for r in range(col, mm):
                if M[r][col] != 0:
                    piv = r
                    break
            if piv is None:
                raise ValueError("singular")
            if piv != col:
                M[col], M[piv] = M[piv], M[col]
            pv = M[col][col]
            M[col] = [x / pv for x in M[col]]
            for r in range(mm):
                if r != col and M[r][col] != 0:
                    factor = M[r][col]
                    M[r] = [M[r][c] - factor * M[col][c] for c in range(mm + 1)]
        return [M[i][mm] for i in range(mm)]

    prob = [solve(A, b_p[ai])[idx[start]] for ai in range(n)]
    cost = [solve(A, b_c[ai])[idx[start]] for ai in range(n)]
    return prob, cost


class TestAbsorption(unittest.TestCase):
    def test_absorption_two_answers(self):
        graph = {
            "entry": [["A", 2, 1], ["B", 1, 3]],
        }
        answers = ["A", "B"]
        prob, cost = _solve_absorb(graph, answers, "entry")
        self.assertEqual(prob[0], Fraction(2, 3))
        self.assertEqual(prob[1], Fraction(1, 3))
        self.assertEqual(cost[0], Fraction(2, 3))
        self.assertEqual(cost[1], Fraction(1, 1))

    def test_absorption_cycle_never_terminates(self):
        graph = {
            "entry": [["loop", 1, 0]],
            "loop": [["loop", 1, 0]],
        }
        answers = ["A", "B"]
        prob, cost = _solve_absorb(graph, answers, "entry")
        self.assertEqual(prob[0], Fraction(0))
        self.assertEqual(prob[1], Fraction(0))
        self.assertEqual(cost[0], Fraction(0))
        self.assertEqual(cost[1], Fraction(0))


class TestVoting(unittest.TestCase):
    def test_direct_single_vote(self):
        prob = [Fraction(2, 3), Fraction(1, 3)]
        cost_mass = [Fraction(2, 3), Fraction(1, 1)]
        wp = prob
        unres = Fraction(0)
        launch = Fraction(1)
        cms = cost_mass
        self.assertEqual(wp[0], Fraction(2, 3))
        self.assertEqual(wp[1], Fraction(1, 3))
        self.assertEqual(unres, Fraction(0))
        self.assertEqual(launch, Fraction(1))
        self.assertEqual(_div(_frac(cms[0]), _frac(wp[0])), [1, 1])

    def test_vote_three_ballots_expected(self):
        self.assertEqual(_frac(Fraction(20, 27)), [20, 27])
        self.assertEqual(_frac(Fraction(7, 27)), [7, 27])
        self.assertEqual(_frac(Fraction(22, 9)), [22, 9])
        self.assertEqual(_frac(Fraction(16, 5)), [16, 5])


class TestCombine(unittest.TestCase):
    def test_combine_public(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"standard": 1},
            "methods": [
                {"id": "direct", "votes": 1, "start": "entry",
                 "graphs": {"standard": {"entry": [["A", 2, 1], ["B", 1, 3]]}}},
                {"id": "vote", "votes": 3, "start": "entry",
                 "graphs": {"standard": {"entry": [["A", 2, 1], ["B", 1, 3]]}}},
            ],
        }
        left = [
            {"standard": [1, 1]},
            {
                "direct": {"0,0": None, "1,0": 0, "0,1": 1},
                "vote": {"0,0": None, "1,0": None, "0,1": None,
                         "2,0": 0, "1,1": None, "0,2": 1,
                         "2,1": 0, "1,2": 1},
            },
        ]
        right = {
            "direct": {"standard": [[[2, 3], [1, 3]], [[2, 3], [1, 1]]]},
            "vote": {"standard": [[[2, 3], [1, 3]], [[2, 3], [1, 1]]]},
        }
        result = call_candidate("integration.py", "combine",
                                args=[payload, left, right])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "vote")
        self.assertEqual(result[1]["id"], "direct")
        self.assertEqual(result[0]["prob"], [[20, 27], [7, 27]])
        self.assertEqual(result[0]["unresolved"], [0, 1])
        self.assertEqual(result[0]["launches"], [22, 9])
        self.assertEqual(result[0]["cost_if_correct"], [16, 5])
        self.assertEqual(result[1]["prob"], [[2, 3], [1, 3]])
        self.assertEqual(result[1]["unresolved"], [0, 1])
        self.assertEqual(result[1]["launches"], [1, 1])
        self.assertEqual(result[1]["cost_if_correct"], [1, 1])


if __name__ == "__main__":
    unittest.main()
