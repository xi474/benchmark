import json
from hashlib import sha256


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    seed = payload["seed"]
    records = payload["records"]

    # left: relationship windows [start, end, from, to]
    # right: record subjects [table, id, time, [tenant, subject]]
    windows = left
    subjects = right

    # Build union-find over all (tenant, subject) pairs that appear anywhere.
    # Each record's own time determines which windows are active.
    # Canonical subject is the lexicographically smallest (tenant, subject) in
    # the connected component, and different tenants never merge directly.

    # Collect all distinct subjects.
    all_subjects = set()
    for w in windows:
        all_subjects.add(tuple(w[0]))
        all_subjects.add(tuple(w[1]))
    for s in subjects:
        all_subjects.add(tuple(s[3]))

    # For each record time, compute the equivalence closure.
    # Since there are at most 200 distinct times, group records by time.
    from collections import defaultdict
    by_time = defaultdict(list)
    for idx, s in enumerate(subjects):
        by_time[s[2]].append(idx)

    # Precompute active windows per time.
    times = sorted(by_time.keys())
    token_by_subject = {}

    def find(parent, x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(parent, rank, a, b):
        ra, rb = find(parent, a), find(parent, b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for t in times:
        parent = {s: s for s in all_subjects}
        rank = {s: 0 for s in all_subjects}
        for w in windows:
            frm, to = w[2], w[3]
            if frm <= t < to:
                union(parent, rank, tuple(w[0]), tuple(w[1]))
        # Compute canonical for each subject at this time.
        comp = {}
        for s in all_subjects:
            r = find(parent, s)
            comp.setdefault(r, s)
            if s < comp[r]:
                comp[r] = s
        for idx in by_time[t]:
            s = tuple(subjects[idx][3])
            canonical = comp[find(parent, s)]
            token_by_subject[s] = canonical

    # Build output records.
    out_records = []
    for s in subjects:
        table, rid, t, subj = s
        canonical = token_by_subject[tuple(subj)]
        raw = json.dumps(
            [str(seed), canonical[0], canonical[1]],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        token = "ref_" + sha256(raw).hexdigest()[:12]
        out_records.append({"table": table, "id": rid, "time": t, "token": token})

    return {"records": out_records}
