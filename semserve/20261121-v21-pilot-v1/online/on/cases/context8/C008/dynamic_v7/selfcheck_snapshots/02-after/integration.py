import json
from hashlib import sha256


def _token(seed, tenant, subject):
    raw = json.dumps([str(seed), tenant, subject], ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return "ref_" + sha256(raw).hexdigest()[:12]


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    seed = payload["seed"]
    records = payload["records"]
    windows = left  # [start, end, from, to]
    subjects = right  # [table, id, time, [tenant, subject]]

    # Collect all distinct times at which records occur.
    times = sorted({r["time"] for r in records})

    # Map each (tenant, subject) to its canonical representative at each record time.
    # For each record time, build the union-find over relationships active at that time.
    result_records = []
    for rec in records:
        t = rec["time"]
        # Active relationships: from <= t < to
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for start, end, frm, to in windows:
            if frm <= t < to:
                union(tuple(start), tuple(end))

        # Canonical subject: lexicographically smallest (tenant, subject) in component.
        key = (rec["tenant"], rec["subject"])
        root = find(key)
        canonical = min((k for k in parent if find(k) == root), default=key)
        token = _token(seed, canonical[0], canonical[1])
        result_records.append({
            "table": rec["table"],
            "id": rec["id"],
            "time": rec["time"],
            "token": token,
        })

    return {"records": result_records}
