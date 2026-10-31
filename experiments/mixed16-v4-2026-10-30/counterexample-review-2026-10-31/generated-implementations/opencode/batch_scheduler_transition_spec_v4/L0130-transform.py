from bisect import bisect_right


def _is_int(x):
    return type(x) is int


def _nonempty_text(x, field):
    if not isinstance(x, str) or x.strip() == '':
        raise ValueError(f'{field} must be a non-empty string')
    return x


def _compatible(a, b, cooldown):
    if a['end'] <= b['end']:
        return a['end'] + cooldown <= b['start']
    return b['end'] + cooldown <= a['start']


def _max_value(windows, cooldown):
    if not windows:
        return 0
    ws = sorted(windows, key=lambda w: (w['end'], w['start'], w['id']))
    ends = [w['end'] for w in ws]
    starts = [w['start'] for w in ws]
    n = len(ws)
    dp = [0] * (n + 1)
    for i in range(1, n + 1):
        j = bisect_right(ends, starts[i - 1] - cooldown) - 1
        take = ws[i - 1]['value'] + (dp[j + 1] if j >= 0 else 0)
        dp[i] = max(dp[i - 1], take)
    return dp[n]


def transform(payloads, contract):
    if not payloads:
        raise ValueError('missing input payload')
    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError('first payload must be an object')
    windows = data.get('windows')
    if windows is None or not isinstance(windows, list):
        raise ValueError("'windows' must be a list")

    cooldown = contract.get('cooldown')
    if not _is_int(cooldown) or cooldown < 0:
        raise ValueError('cooldown must be a non-negative int')

    seen = set()
    parsed = []
    for w in windows:
        if not isinstance(w, dict):
            raise ValueError('each window must be an object')
        wid = _nonempty_text(w.get('id'), 'window.id')
        stripped = wid.strip()
        if stripped in seen:
            raise ValueError('duplicate window id')
        seen.add(stripped)
        start = w.get('start')
        end = w.get('end')
        value = w.get('value')
        if not _is_int(start) or start < 0:
            raise ValueError('window.start must be int >= 0')
        if not _is_int(end) or end <= start:
            raise ValueError('window.end must be int > start')
        if not _is_int(value):
            raise ValueError('window.value must be int')
        parsed.append({'id': stripped, 'start': start, 'end': end, 'value': value})

    n = len(parsed)
    if n == 0:
        return {'name': contract['name'], 'result': {'selected': [], 'value': 0}}

    best_value = _max_value(parsed, cooldown)

    candidates = sorted(parsed, key=lambda w: w['id'])
    chosen = []
    last_id = None
    remaining = best_value

    def ok_with_chosen(w, extra=None):
        base = chosen + ([extra] if extra is not None else [])
        for p in base:
            if not _compatible(w, p, cooldown):
                return False
        return True

    while remaining > 0:
        found = False
        for w in candidates:
            if last_id is not None and w['id'] <= last_id:
                continue
            if not ok_with_chosen(w):
                continue
            new_remaining = remaining - w['value']
            if new_remaining < 0:
                continue
            avail = [
                x for x in candidates
                if x['id'] > w['id'] and ok_with_chosen(x, w)
            ]
            if _max_value(avail, cooldown) == new_remaining:
                chosen.append(w)
                last_id = w['id']
                remaining = new_remaining
                found = True
                break
        if not found:
            raise ValueError('internal error: no feasible completion')

    selected = sorted(w['id'] for w in chosen)
    return {'name': contract['name'], 'result': {'selected': selected, 'value': best_value}}
