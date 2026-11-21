import json
from pathlib import Path


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value


def _compute_x(students, grades):
    sums = {}
    counts = {}
    for row in grades:
        student, course, score = row
        if course not in (1, 2):
            continue
        if score is None:
            continue
        sums[student] = sums.get(student, 0) + score
        counts[student] = counts.get(student, 0) + 1
    x = {}
    for s in students:
        x[s] = round(sums[s] * 100 / counts[s])
    return x


def _compute_y(buyers, orders):
    y = {}
    for order in orders:
        buyer = order['buyer']
        total = 0
        for line in order['lines']:
            cats, qty, price = line
            if 'Electronics' in cats or 'Cameras' in cats:
                total += qty * price
        y[buyer] = y.get(buyer, 0) + total
    return y


def _build_confidence(evidence, drop_source):
    per_source = {}
    for src, student, buyer, strength in evidence:
        if drop_source is not None and src == drop_source:
            continue
        per_source.setdefault(src, {}).setdefault((student, buyer), 0)
        if strength > per_source[src][(student, buyer)]:
            per_source[src][(student, buyer)] = strength
    conf = {}
    for src, pairs in per_source.items():
        for (student, buyer), strength in pairs.items():
            conf[(student, buyer)] = conf.get((student, buyer), 0) + strength
    return conf


def _solve(students, buyers, conf):
    n = len(students)
    adj = {}
    for i, s in enumerate(students):
        adj[i] = []
        for j, b in enumerate(buyers):
            if (s, b) in conf:
                adj[i].append(j)

    matchings = []
    used = [False] * n

    def backtrack(i, current, minc, totalc):
        if i == n:
            matchings.append((minc, totalc, list(current)))
            return
        for j in adj[i]:
            if not used[j]:
                used[j] = True
                c = conf[(students[i], buyers[j])]
                backtrack(i + 1, current + [j], min(minc, c), totalc + c)
                used[j] = False

    backtrack(0, [], float('inf'), 0)

    if not matchings:
        return None

    best_min = max(m[0] for m in matchings)
    candidates = [m for m in matchings if m[0] == best_min]
    best_total = max(m[1] for m in candidates)
    optimal = [m for m in candidates if m[1] == best_total]
    return optimal


def _result_for(students, buyers, x, y, conf):
    optimal = _solve(students, buyers, conf)
    if optimal is None:
        return None

    n = len(students)
    sx = sum(x[s] for s in students)
    sy = sum(y[b] for b in buyers)

    def num_of(m):
        sxy = sum(x[students[i]] * y[buyers[m[2][i]]] for i in range(n))
        return n * sxy - sx * sy

    nums = [num_of(m) for m in optimal]
    min_num = min(nums)
    max_num = max(nums)

    # Buyer vectors are reported in ascending student-ID order.
    order = sorted(range(n), key=lambda i: students[i])

    def buyer_vec(m):
        return [buyers[m[2][i]] for i in order]

    # min_buyers: lexicographically smallest buyer vector among ALL optimal matchings.
    min_vec = min(buyer_vec(m) for m in optimal)
    # max_buyers: lexicographically largest buyer vector among ALL optimal matchings.
    max_vec = max(buyer_vec(m) for m in optimal)

    # forced: pairs present in all optimal matchings, sorted by student ID ascending.
    forced = []
    for i in order:
        s = students[i]
        jset = set(m[2][i] for m in optimal)
        if len(jset) == 1:
            forced.append([s, buyers[jset.pop()]])
    forced.sort(key=lambda p: p[0])

    return {
        'floor': max(m[0] for m in optimal),
        'total': max(m[1] for m in optimal),
        'count': len(optimal),
        'min_num': min_num,
        'max_num': max_num,
        'min_buyers': min_vec,
        'max_buyers': max_vec,
        'forced': forced,
    }


def transform(payload):
    students = payload['students']
    buyers = payload['buyers']
    grades = payload['grades']
    orders = payload['orders']
    evidence = payload['evidence']
    drops = payload['drop']

    x = _compute_x(students, grades)
    y = _compute_y(buyers, orders)

    results = []
    for drop in drops:
        conf = _build_confidence(evidence, drop)
        result = _result_for(students, buyers, x, y, conf)
        results.append({'drop': drop, 'result': result})

    return results
