from pathlib import Path
import json


def transform(payload):
    initial = payload["initial"]
    pools = payload["pools"]
    feeds = payload["feeds"]
    tasks = payload["tasks"]

    # Index tasks by id.
    by_id = {t["id"]: t for t in tasks}

    # Per-pool round-robin cursor.
    pool_cursor = {p: 0 for p in pools}
    # Per-(host, stream) round-robin cursor.
    feed_cursor = {}
    for host, streams in feeds.items():
        for stream in streams:
            feed_cursor[(host, stream)] = 0

    # Facts per host.
    facts = dict(initial)

    # Read counters.
    pool_reads = {p: 0 for p in pools}
    feed_reads = {host: {s: 0 for s in streams} for host, streams in feeds.items()}

    # Committed deltas per task (for parent sums).
    committed = {}

    # Result records.
    result = {}

    remaining = set(by_id)

    while remaining:
        # Tasks whose needs are all committed this round.
        ready = [tid for tid in remaining
                 if all(n in committed for n in by_id[tid]["needs"])]
        ready.sort()  # lexicographic by id

        # Snapshot facts at round start.
        round_base = dict(facts)

        # For each ready task, select host and batch (consuming selectors once).
        selections = []
        for tid in ready:
            t = by_id[tid]
            pool = t["pool"]
            hosts = pools[pool]
            host = hosts[pool_cursor[pool] % len(hosts)]
            pool_cursor[pool] += 1
            pool_reads[pool] += 1

            stream = t["stream"]
            batches = feeds[host][stream]
            idx = feed_cursor[(host, stream)] % len(batches)
            feed_cursor[(host, stream)] += 1
            feed_reads[host][stream] += 1
            items = batches[idx]

            selections.append((tid, host, items))

        # Compute base, parent, delta for each selected task.
        deltas = {}
        for tid, host, items in selections:
            t = by_id[tid]
            base = round_base[host]
            parent = sum(committed[n] for n in t["needs"])
            delta = sum((base + item) * (1 + parent) for item in items)
            deltas[tid] = delta
            result[tid] = {
                "host": host,
                "items": items,
                "base": base,
                "parent": parent,
                "delta": delta,
                "attempts": t["attempts"],
            }

        # Commit all successful deltas at end of round.
        for tid, delta in deltas.items():
            host = result[tid]["host"]
            facts[host] += delta
            committed[tid] = delta
            remaining.discard(tid)

    return {
        "tasks": result,
        "facts": facts,
        "pool_reads": pool_reads,
        "feed_reads": feed_reads,
    }


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
