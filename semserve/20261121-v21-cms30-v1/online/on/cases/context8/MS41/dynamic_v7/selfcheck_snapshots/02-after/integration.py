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


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md.

    left  = [prior_map, method_decision_table]
    right = {method_id: {profile: [absorption_probs, weighted_cost_mass]}}
    """
    answers = payload["answers"]
    correct = payload["correct"]
    profiles = payload["profiles"]
    methods = payload["methods"]

    n = len(answers)
    correct_idx = answers.index(correct)

    prior = left[0]
    decision_table = left[1]

    results = []
    for method in methods:
        mid = method["id"]
        votes = method["votes"]
        table = decision_table[mid]
        absorption = right[mid]

        # Per-answer single-ballot absorption probability and weighted cost mass,
        # averaged over profiles by prior weight.
        prob = [[0, 1] for _ in range(n)]
        cost_mass = [[0, 1] for _ in range(n)]
        for profile, weight in profiles.items():
            pr = prior[profile]
            ap, cm = absorption[profile]
            for i in range(n):
                prob[i] = _add(prob[i], _mul(pr, ap[i]))
                cost_mass[i] = _add(cost_mass[i], _mul(pr, cm[i]))

        # Build all reachable count states from the decision table.
        states = {}
        for key, decision in table.items():
            counts = tuple(int(x) for x in key.split(","))
            states[counts] = decision

        ordered = sorted(states.keys(), key=lambda s: -sum(s))

        win_prob = {}
        unresolved = {}
        launches = {}
        cost_mass_state = {}

        for state in ordered:
            decision = states[state]
            total = sum(state)
            if decision is not None:
                wp = [[0, 1] for _ in range(n)]
                wp[decision] = [1, 1]
                win_prob[state] = wp
                unresolved[state] = [0, 1]
                launches[state] = [0, 1]
                cost_mass_state[state] = [[0, 1] for _ in range(n)]
            elif total == votes:
                win_prob[state] = [[0, 1] for _ in range(n)]
                unresolved[state] = [1, 1]
                launches[state] = [0, 1]
                cost_mass_state[state] = [[0, 1] for _ in range(n)]
            else:
                wp = [[0, 1] for _ in range(n)]
                unres = [0, 1]
                launch = [1, 1]
                cms = [[0, 1] for _ in range(n)]
                for i in range(n):
                    ai = prob[i]
                    cmi = cost_mass[i]
                    next_state = list(state)
                    next_state[i] += 1
                    next_state = tuple(next_state)
                    nwp = win_prob[next_state]
                    nunres = unresolved[next_state]
                    nlaunch = launches[next_state]
                    ncms = cost_mass_state[next_state]
                    for j in range(n):
                        wp[j] = _add(wp[j], _mul(ai, nwp[j]))
                        cms[j] = _add(cms[j], _mul(cmi, nwp[j]))
                        cms[j] = _add(cms[j], _mul(ai, ncms[j]))
                    unres = _add(unres, _mul(ai, nunres))
                    launch = _add(launch, _mul(ai, nlaunch))
                # Unresolved ballot probability u = 1 - sum(prob).
                u = [1, 1]
                for i in range(n):
                    u = _add(u, _mul([-1, 1], prob[i]))
                unres = _add(unres, u)
                win_prob[state] = wp
                unresolved[state] = unres
                launches[state] = launch
                cost_mass_state[state] = cms

        zero = tuple([0] * n)
        wp0 = win_prob[zero]
        unres0 = unresolved[zero]
        launch0 = launches[zero]
        cms0 = cost_mass_state[zero]

        prob_out = [wp0[i] for i in range(n)]
        unresolved_out = unres0

        if wp0[correct_idx][0] == 0:
            cost_if_correct = None
        else:
            cost_if_correct = _div(cms0[correct_idx], wp0[correct_idx])

        results.append({
            "id": mid,
            "prob": prob_out,
            "unresolved": unresolved_out,
            "launches": launch0,
            "cost_if_correct": cost_if_correct,
        })

    def correct_prob_key(r):
        p = r["prob"][correct_idx]
        return -p[0] / p[1]

    results.sort(key=lambda r: (correct_prob_key(r), r["id"]))

    return results
