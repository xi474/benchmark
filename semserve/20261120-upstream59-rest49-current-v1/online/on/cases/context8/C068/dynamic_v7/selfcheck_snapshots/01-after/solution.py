"""C068: cancellable waiters with shared in-flight TTL cache."""

import json


def transform(payload):
    ttl = payload["ttl"]
    events = payload["events"]

    results = []
    loads = []

    # cache: key -> {"value": ..., "error": ..., "expires": ...}
    cache = {}
    # in-flight loads: key -> {"started_at": ..., "finished_at": ..., "waiters": [ids]}
    inflight = {}
    # load start order for same-time completion ordering
    load_order = []

    next_cleanup = 16 * ttl

    def cleanup_all(now):
        nonlocal next_cleanup
        for k in list(cache.keys()):
            if cache[k]["expires"] <= now:
                del cache[k]
        next_cleanup = now + 16 * ttl

    def cleanup_key(now, key):
        if key in cache and cache[key]["expires"] <= now:
            del cache[key]

    def complete_load(key, now):
        """Complete an in-flight load at time now."""
        entry = inflight[key]
        started_at = entry["started_at"]
        finished_at = now
        # stamp cache
        cache[key] = {
            "value": entry["value"],
            "error": entry["error"],
            "expires": now + ttl,
        }
        loads.append({
            "key": key,
            "started_at": started_at,
            "finished_at": finished_at,
        })
        # resolve waiters
        for wid in entry["waiters"]:
            results.append({
                "id": wid,
                "status": "ok" if entry["error"] is None else "error",
                "value": entry["value"] if entry["error"] is None else None,
                "error": entry["error"],
                "finished_at": finished_at,
            })
        del inflight[key]

    def process_due_loads(now):
        """Complete loads whose finish time <= now, in start order."""
        due = [k for k in load_order if k in inflight and inflight[k]["finished_at"] <= now]
        due.sort(key=lambda k: (inflight[k]["started_at"], load_order.index(k)))
        for k in due:
            complete_load(k, inflight[k]["finished_at"])

    for ev in events:
        op = ev["op"]
        time = ev["time"]

        if op == "advance":
            process_due_loads(time)
            continue

        if op == "cancel":
            # cancel and completed load at same time: completion first
            process_due_loads(time)
            cid = ev["id"]
            # find the in-flight load containing this waiter
            for k in list(inflight.keys()):
                if cid in inflight[k]["waiters"]:
                    inflight[k]["waiters"].remove(cid)
                    results.append({
                        "id": cid,
                        "status": "cancelled",
                        "value": None,
                        "error": "cancelled",
                        "finished_at": time,
                    })
                    break
            continue

        if op == "get":
            gid = ev["id"]
            key = ev["key"]
            delay = ev["delay"]
            value = ev["value"]
            error = ev.get("error", None)

            # complete due loads first
            process_due_loads(time)

            # cleanup check on access
            if time >= next_cleanup:
                cleanup_all(time)
            cleanup_key(time, key)

            if key in cache:
                # cache hit
                results.append({
                    "id": gid,
                    "status": "ok" if cache[key]["error"] is None else "error",
                    "value": cache[key]["value"] if cache[key]["error"] is None else None,
                    "error": cache[key]["error"],
                    "finished_at": time,
                })
                continue

            # miss: start or join in-flight load
            if key in inflight:
                inflight[key]["waiters"].append(gid)
                continue

            # start new load
            started_at = time
            finished_at = time + delay
            inflight[key] = {
                "started_at": started_at,
                "finished_at": finished_at,
                "value": value,
                "error": error,
                "waiters": [gid],
            }
            load_order.append(key)

            # delay == 0 completes within this get
            if delay == 0:
                complete_load(key, time)

    # At end, all gets are completed or cancelled (guaranteed by input).
    # Complete any remaining in-flight loads (shouldn't happen per contract,
    # but be safe).
    remaining = [k for k in load_order if k in inflight]
    remaining.sort(key=lambda k: (inflight[k]["started_at"], load_order.index(k)))
    for k in remaining:
        complete_load(k, inflight[k]["finished_at"])

    # sort cache by key
    cache_list = [
        {
            "key": k,
            "value": cache[k]["value"],
            "error": cache[k]["error"],
            "expires": cache[k]["expires"],
        }
        for k in sorted(cache.keys())
    ]

    return {
        "results": results,
        "loads": loads,
        "cache": cache_list,
        "next_cleanup": next_cleanup,
    }


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
