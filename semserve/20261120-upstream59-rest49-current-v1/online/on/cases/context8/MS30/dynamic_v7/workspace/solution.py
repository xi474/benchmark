from pathlib import Path
import json


def _grade_letter(ratio):
    if ratio < 0.60:
        return "N"
    if ratio < 0.75:
        return "D"
    return "P"


def _student_letters(grades):
    # grades rows: [student, course, score_or_null, max]
    acc = {}
    for student, course, score, mx in grades:
        if course not in (16, 17):
            continue
        if score is None or mx is None:
            continue
        if mx == 0:
            continue
        acc.setdefault(student, []).append(score / mx)
    out = {}
    for student, ratios in acc.items():
        avg = sum(ratios) / len(ratios)
        out[student] = _grade_letter(avg)
    return out


def _select_events(market, top):
    # market rows: [event_id, day, open, close]
    if not market:
        return []
    L = max(row[1] for row in market)
    rows = [r for r in market if L - 29 <= r[1] <= L]
    rows.sort(key=lambda r: (-abs(r[3] - r[2]) / r[2], r[0]))
    return [r[0] for r in rows[:top]]


def _tier_rank(tiers, letter):
    # rank of letter within tiers; lower is better. None if not listed.
    for i, group in enumerate(tiers):
        if letter in group:
            return i
    return None


def _student_rank(prefs, student, event):
    # rank of event within student's preference groups; lower is better.
    # None if event not listed (unacceptable).
    groups = prefs.get(student, [])
    for i, group in enumerate(groups):
        if event in group:
            return i
    return None


def _acceptable(student, event, prefs, rooms):
    # both sides acceptable
    if _student_rank(prefs, student, event) is None:
        return False
    letter = student_letters_cache.get(student)
    if letter is None:
        return False
    if _tier_rank(rooms[event]["tiers"], letter) is None:
        return False
    return True


def _is_stable(mapping, students, events, prefs, rooms, capacities):
    # mapping: dict student -> event (or None for unassigned)
    # weak stability: no blocking pair (unassigned student s, open event w)
    # such that s strictly prefers w over current, and w has free seat or
    # strictly prefers s over some assigned student.
    assigned = {s: e for s, e in mapping.items() if e is not None}
    # occupancy
    occ = {e: 0 for e in events}
    for e in assigned.values():
        occ[e] += 1

    # student rank cache
    srank = {}
    for s in students:
        for e in events:
            srank[(s, e)] = _student_rank(prefs, s, e)

    # event tier rank cache
    erank = {}
    for e in events:
        for s in students:
            letter = student_letters_cache.get(s)
            erank[(e, s)] = _tier_rank(rooms[e]["tiers"], letter)

    for s in students:
        cur = mapping.get(s)
        cur_rank = srank[(s, cur)] if cur is not None else None
        for w in events:
            if capacities[w] == 0:
                continue
            sr = srank[(s, w)]
            if sr is None:
                continue
            # s must strictly prefer w over current
            if cur is not None:
                if cur_rank is None or sr >= cur_rank:
                    continue
            # else unassigned: any acceptable w is strictly preferred
            # (unassigned is worse than any acceptable event)
            # w must have free seat or strictly prefer s over some assigned
            if occ[w] < capacities[w]:
                # blocking
                return False
            # check if w strictly prefers s over some assigned student
            s_tier = erank[(w, s)]
            if s_tier is None:
                continue
            for t in assigned:
                if assigned[t] != w:
                    continue
                t_tier = erank[(w, t)]
                if t_tier is None:
                    continue
                if s_tier < t_tier:
                    return False
    return True


def _enumerate_stable(students, events, prefs, rooms, capacities):
    # enumerate all weakly stable matchings (student -> event or None)
    # each student at most one seat, each event at most capacity.
    # brute force over assignments; components are small (<=8 students).
    results = []
    n = len(students)
    # options per student: None plus acceptable events
    options = []
    for s in students:
        opts = [None]
        for e in events:
            if _acceptable(s, e, prefs, rooms):
                opts.append(e)
        options.append(opts)

    # recursive assignment with capacity tracking
    occ = {e: 0 for e in events}
    mapping = {}

    def rec(i):
        if i == n:
            if _is_stable(mapping, students, events, prefs, rooms, capacities):
                results.append(dict(mapping))
            return
        s = students[i]
        for e in options[i]:
            if e is not None:
                if occ[e] >= capacities[e]:
                    continue
                occ[e] += 1
                mapping[s] = e
                rec(i + 1)
                del mapping[s]
                occ[e] -= 1
            else:
                mapping[s] = None
                rec(i + 1)
                del mapping[s]

    rec(0)
    return results


def transform(payload):
    global student_letters_cache
    grades = payload["grades"]
    market = payload["market"]
    rooms = payload["rooms"]
    prefs = payload["prefs"]
    top = payload["top"]
    cancels = payload["cancel"]

    student_letters_cache = _student_letters(grades)
    students = sorted(student_letters_cache.keys())

    selected = _select_events(market, top)

    out = []
    for cancel in cancels:
        closed = set(cancel)
        events = [e for e in selected if e not in closed]
        capacities = {e: rooms[e]["capacity"] for e in events}

        matchings = _enumerate_stable(students, events, prefs, rooms, capacities)

        # group by number assigned
        from collections import Counter
        size_counts = Counter()
        for m in matchings:
            cnt = sum(1 for e in m.values() if e is not None)
            size_counts[cnt] += 1

        sizes = sorted([[cnt, num] for cnt, num in size_counts.items()])

        max_cnt = max(size_counts) if size_counts else 0
        max_matchings = [m for m in matchings
                         if sum(1 for e in m.values() if e is not None) == max_cnt]

        # forced: pairs present in all max matchings
        forced = []
        if max_matchings:
            pairs = set()
            for s in students:
                for e in events:
                    pairs.add((s, e))
            for (s, e) in pairs:
                if all(m.get(s) == e for m in max_matchings):
                    forced.append([s, e])
            forced.sort()

        # example: lexicographically smallest vector of assigned events by
        # student id ascending; unassigned -> ""
        example = None
        if max_matchings:
            vectors = []
            for m in max_matchings:
                vec = [m.get(s) or "" for s in students]
                vectors.append(vec)
            example = min(vectors)

        out.append({
            "sizes": sizes,
            "forced": forced,
            "example": example,
        })

    return out


from pathlib import Path
import json


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
