import re
from collections import defaultdict


def _edit1(a, b):
    """True if a and b differ by at most one substitution/insertion/deletion."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        d = sum(1 for x, y in zip(a, b) if x != y)
        return d <= 1
    if len(a) < len(b):
        a, b = b, a
    i = j = 0
    skipped = False
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            if skipped:
                return False
            skipped = True
            i += 1
    return True


def combine(payload, left, right):
    records = []
    for pos, obj in left:
        records.append((pos, obj))
    for pos, obj in right:
        records.append((pos, obj))

    ambiguous = set(payload.get("ambiguous_names", []) or [])

    n = len(records)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_ssn_full = defaultdict(list)
    by_mail = defaultdict(list)
    by_dob = defaultdict(list)

    for i, (pos, o) in enumerate(records):
        ssn = o.get("ssn", "")
        if len(ssn) == 9:
            by_ssn_full[ssn].append(i)
        mail = o.get("mail", "")
        if mail:
            by_mail[mail].append(i)
        dob = o.get("dob", "")
        if dob:
            by_dob[dob].append(i)

    # 1. Full 9-digit government id: strong, unique in normal domain.
    for ssn, idxs in by_ssn_full.items():
        for k in range(1, len(idxs)):
            union(idxs[0], idxs[k])

    # 2. Exact email + matching dob + matching non-ambiguous first name.
    for mail, idxs in by_mail.items():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                oi, oj = records[i][1], records[j][1]
                if oi.get("dob") and oi["dob"] == oj.get("dob"):
                    fi, fj = oi.get("first", ""), oj.get("first", "")
                    if fi and fi == fj and fi not in ambiguous:
                        union(i, j)

    # 3. Email with one-character edit distance + matching dob + matching
    #    last name (last name is not ambiguous; email edit1 + dob + last is
    #    strong evidence of same person even with ambiguous first name).
    for dob, idxs in by_dob.items():
        if len(idxs) < 2:
            continue
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                oi, oj = records[i][1], records[j][1]
                mi, mj = oi.get("mail", ""), oj.get("mail", "")
                if mi and mj and mi != mj and _edit1(mi, mj):
                    li, lj = oi.get("last", ""), oj.get("last", "")
                    if li and li == lj:
                        union(i, j)

    # 4. Non-ambiguous full first name + last name + dob.
    name_dob = defaultdict(list)
    for i, (pos, o) in enumerate(records):
        first = o.get("first", "")
        last = o.get("last", "")
        dob = o.get("dob", "")
        if first and last and dob:
            name_dob[(first, last, dob)].append(i)
    for key, idxs in name_dob.items():
        first = key[0]
        if first in ambiguous:
            continue
        for k in range(1, len(idxs)):
            union(idxs[0], idxs[k])

    # 5. Link 4-digit government id to a 9-digit government id via matching
    #    last-4 digits + last name + dob.
    for i, (pos, o) in enumerate(records):
        ssn = o.get("ssn", "")
        if len(ssn) != 4:
            continue
        last = o.get("last", "")
        dob = o.get("dob", "")
        if not (last and dob):
            continue
        for j, (pos2, o2) in enumerate(records):
            if i == j:
                continue
            ssn2 = o2.get("ssn", "")
            if len(ssn2) == 9 and ssn2.endswith(ssn) and o2.get("last") == last and o2.get("dob") == dob:
                union(i, j)

    groups = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(records[i][1]["id"])

    clusters = [sorted(ids) for ids in groups.values()]
    return {"clusters": clusters}
