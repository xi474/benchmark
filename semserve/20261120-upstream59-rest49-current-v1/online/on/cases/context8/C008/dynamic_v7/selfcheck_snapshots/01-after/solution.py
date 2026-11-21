from pathlib import Path
import json
import hashlib

DEFAULT_TO = 10 ** 18


def _token(seed, tenant, subject):
    raw = json.dumps(
        [str(seed), tenant, subject],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "ref_" + hashlib.sha256(raw).hexdigest()[:12]


def transform(payload):
    seed = payload["seed"]
    records = payload["records"]
    links = payload.get("links", [])
    merges = payload.get("merges", [])

    # Build the list of edges active at each distinct record time.
    # An edge is active at time t iff from <= t < to.
    edges = []
    for e in links:
        a = tuple(e["a"])
        b = tuple(e["b"])
        frm = e.get("from", 0)
        to = e.get("to", DEFAULT_TO)
        edges.append((a, b, frm, to))
    for e in merges:
        a = tuple(e["a"])
        b = tuple(e["b"])
        frm = e.get("from", 0)
        to = e.get("to", DEFAULT_TO)
        edges.append((a, b, frm, to))

    # Distinct times in first-appearance order.
    times = []
    seen_times = set()
    for r in records:
        t = r["time"]
        if t not in seen_times:
            seen_times.add(t)
            times.append(t)

    # For each time, compute connected components of active edges.
    # Cache canonical subject per (time, subject) to reuse across records.
    time_canonical = {}

    def canonical_at(t):
        if t in time_canonical:
            return time_canonical[t]
        # Union-find over all subjects appearing in active edges.
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for (a, b, frm, to) in edges:
            if frm <= t < to:
                union(a, b)

        # Map each subject to its component's lexicographically smallest tuple.
        comp_min = {}
        for node in parent:
            r = find(node)
            if r not in comp_min or node < comp_min[r]:
                comp_min[r] = node
        result = {node: comp_min[find(node)] for node in parent}
        time_canonical[t] = result
        return result

    out_records = []
    for r in records:
        t = r["time"]
        subject = (r["tenant"], r["subject"])
        canon = canonical_at(t).get(subject, subject)
        out_records.append({
            "table": r["table"],
            "id": r["id"],
            "time": t,
            "token": _token(seed, canon[0], canon[1]),
        })

    return {"records": out_records}


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return value
