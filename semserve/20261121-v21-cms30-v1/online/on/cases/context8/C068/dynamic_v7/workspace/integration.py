def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    ttl = payload["ttl"]
    events = payload["events"]

    # left: cleanup_clock -> {position_str: next_cleanup_after_trigger}
    # right: load_proposals -> {position_str: [finished_at, value, error]}
    cleanup_triggers = left or {}
    proposals = right or {}

    results = []
    loads = []
    cache = {}  # key -> {"value":..., "error":..., "expires":...}
    in_flight = {}  # key -> {"started_at":..., "finished_at":..., "value":..., "error":..., "waiters":[...]}
    next_cleanup = 16 * ttl

    def finish_load(key):
        load = in_flight.pop(key)
        finished_at = load["finished_at"]
        cache[key] = {
            "value": load["value"],
            "error": load["error"],
            "expires": finished_at + ttl,
        }
        loads.append({
            "key": key,
            "started_at": load["started_at"],
            "finished_at": finished_at,
        })
        for waiter in load["waiters"]:
            results.append({
                "id": waiter["id"],
                "status": "ok" if load["error"] is None else "error",
                "value": load["value"] if load["error"] is None else None,
                "error": load["error"],
                "finished_at": finished_at,
            })

    def complete_due_loads(now):
        # Complete loads whose finished_at <= now, in load start order.
        due = sorted(
            (k for k, v in in_flight.items() if v["finished_at"] <= now),
            key=lambda k: in_flight[k]["started_at"],
        )
        for key in due:
            finish_load(key)

    def cleanup_if_needed(now):
        nonlocal next_cleanup
        if now >= next_cleanup:
            for key in [k for k, v in cache.items() if v["expires"] <= now]:
                del cache[key]
            next_cleanup = now + 16 * ttl

    for i, ev in enumerate(events):
        op = ev["op"]
        now = ev["time"]

        if op == "advance":
            complete_due_loads(now)
            continue

        if op == "cancel":
            # Cancel only waiters that have not yet returned.
            target_id = ev["id"]
            for key, load in list(in_flight.items()):
                for waiter in load["waiters"]:
                    if waiter["id"] == target_id:
                        load["waiters"].remove(waiter)
                        results.append({
                            "id": target_id,
                            "status": "cancelled",
                            "value": None,
                            "error": "cancelled",
                            "finished_at": now,
                        })
                        break
            continue

        if op == "get":
            # Complete due loads first (same-time loads complete before the get).
            complete_due_loads(now)
            cleanup_if_needed(now)

            key = ev["key"]
            # Immediately evict this key's expired entry.
            if key in cache and cache[key]["expires"] <= now:
                del cache[key]

            if key in cache:
                entry = cache[key]
                results.append({
                    "id": ev["id"],
                    "status": "ok" if entry["error"] is None else "error",
                    "value": entry["value"] if entry["error"] is None else None,
                    "error": entry["error"],
                    "finished_at": now,
                })
                continue

            if key in in_flight:
                # Join the existing in-flight load; ignore own loader params.
                in_flight[key]["waiters"].append({
                    "id": ev["id"],
                })
                continue

            # Start a new load.
            proposal = proposals.get(str(i))
            if proposal is not None:
                finished_at, value, error = proposal
            else:
                finished_at = now + ev["delay"]
                value = ev["value"]
                error = ev.get("error", None)

            if ev["delay"] == 0:
                # delay=0 completes within this get.
                cache[key] = {
                    "value": value,
                    "error": error,
                    "expires": finished_at + ttl,
                }
                loads.append({
                    "key": key,
                    "started_at": now,
                    "finished_at": finished_at,
                })
                results.append({
                    "id": ev["id"],
                    "status": "ok" if error is None else "error",
                    "value": value if error is None else None,
                    "error": error,
                    "finished_at": finished_at,
                })
            else:
                in_flight[key] = {
                    "started_at": now,
                    "finished_at": finished_at,
                    "value": value,
                    "error": error,
                    "waiters": [{"id": ev["id"]}],
                }

    # At end, all gets are completed or cancelled; complete any remaining loads.
    while in_flight:
        key = min(in_flight, key=lambda k: in_flight[k]["started_at"])
        finish_load(key)

    # Sort cache by key.
    cache_list = [
        {
            "key": key,
            "value": cache[key]["value"],
            "error": cache[key]["error"],
            "expires": cache[key]["expires"],
        }
        for key in sorted(cache)
    ]

    return {
        "results": results,
        "loads": loads,
        "cache": cache_list,
        "next_cleanup": next_cleanup,
    }
