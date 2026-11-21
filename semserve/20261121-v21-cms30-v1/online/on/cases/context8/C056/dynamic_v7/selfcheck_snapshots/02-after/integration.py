def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    tasks = payload["tasks"]
    pools = payload["pools"]
    feeds = payload["feeds"]
    initial = payload["initial"]

    by_id = {t["id"]: t for t in tasks}
    waves = left  # list of batches, each batch is ascending task IDs

    # Stateful selectors: pool cursor per pool, feed cursor per (host, stream).
    pool_cursor = {p: 0 for p in pools}
    feed_cursor = {}
    for host, streams in feeds.items():
        for stream in streams:
            feed_cursor[(host, stream)] = 0

    pool_reads = {p: 0 for p in pools}
    feed_reads = {}
    for host, streams in feeds.items():
        feed_reads[host] = {s: 0 for s in streams}

    facts = dict(initial)
    committed = {}  # task id -> delta (committed)

    result_tasks = {}

    for wave in waves:
        # All tasks in this wave are released simultaneously at round start.
        # Consume selectors in ascending task id order.
        # Each task consumes its delegation selector and one batch selector once.
        # Retries reuse the chosen host, batch, and snapshot.
        selections = {}
        for tid in wave:
            t = by_id[tid]
            pool = t["pool"]
            stream = t["stream"]
            # delegation selector
            hosts = pools[pool]
            host = hosts[pool_cursor[pool] % len(hosts)]
            pool_cursor[pool] += 1
            pool_reads[pool] += 1
            # batch selector
            batches = feeds[host][stream]
            idx = feed_cursor[(host, stream)] % len(batches)
            feed_cursor[(host, stream)] += 1
            feed_reads[host][stream] += 1
            items = list(batches[idx])
            selections[tid] = (host, items)

        # Compute base (round-start fact) and parent (sum of committed deltas of
        # direct parents). All tasks in the wave share the same fact snapshot.
        for tid in wave:
            t = by_id[tid]
            host, items = selections[tid]
            base = facts[host]
            parent = sum(committed[n] for n in t["needs"])
            delta = sum((base + item) * (1 + parent) for item in items)
            result_tasks[tid] = {
                "host": host,
                "items": items,
                "base": base,
                "parent": parent,
                "delta": delta,
                "attempts": t["attempts"],
            }
            committed[tid] = delta

        # After all successful commits in the round, each host's fact increases
        # by the sum of deltas delegated to it.
        for tid in wave:
            host = selections[tid][0]
            facts[host] += committed[tid]

    return {
        "tasks": result_tasks,
        "facts": facts,
        "pool_reads": pool_reads,
        "feed_reads": feed_reads,
    }
