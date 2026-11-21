def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    events = payload.get("events", [])

    fetches = []
    commits = []
    audit = []

    active = []          # active modification ids, ordered
    owed = False         # pending refresh obligation
    loading = False      # a request/retry/refresh is pending
    in_flight = None     # current network request id
    retry_at = None      # scheduled retry due time
    items = []           # committed items
    fetch_counter = 0

    # left: {str(index): [active ids]} for start/finish events
    # right: {str(index): [reason, due] or None} for response events

    def emit_fetch(time):
        nonlocal fetch_counter, in_flight, loading
        fetch_counter += 1
        fid = "fetch-%d" % fetch_counter
        fetches.append({"id": fid, "time": time})
        audit.append({"time": time, "event": "fetch", "id": fid})
        in_flight = fid
        loading = True
        return fid

    def commit(time, new_items, fid):
        nonlocal items, owed, loading, in_flight
        items.extend(new_items)
        commits.append({"time": time, "items": list(new_items)})
        audit.append({"time": time, "event": "committed", "id": fid})
        in_flight = None
        # loading ends only if no further obligation
        if not owed:
            loading = False

    i = 0
    n = len(events)
    while i < n:
        ev = events[i]
        t = ev["time"]
        op = ev.get("op")

        # Timer fires before external events at the same time.
        if retry_at is not None and retry_at <= t:
            retry_at = None
            in_flight = None
            owed = True
            # retry immediately if no modification in flight
            if not active:
                owed = False
                emit_fetch(t)
            # else keep owed; last finish will retry synchronously

        if op == "start":
            mid = ev.get("id")
            if mid not in active:
                active.append(mid)
            audit.append({"time": t, "event": "modification_started", "id": mid})
        elif op == "finish":
            mid = ev.get("id")
            if mid in active:
                active.remove(mid)
            audit.append({"time": t, "event": "modification_finished", "id": mid})
            owed = True
            # if this is the last active modification and we owe, fetch now
            if not active and owed:
                owed = False
                emit_fetch(t)
        elif op == "refresh":
            owed = True
            if not active and not in_flight and retry_at is None:
                owed = False
                emit_fetch(t)
        elif op == "response":
            fid = ev.get("id")
            if ev.get("failed"):
                audit.append({"time": t, "event": "retry_scheduled", "due": t + 2000, "reason": "failure"})
                retry_at = t + 2000
                # keep in_flight until timer fires
            elif ev.get("stale") == 1:
                audit.append({"time": t, "event": "retry_scheduled", "due": t + 1000, "reason": "stale"})
                retry_at = t + 1000
                # keep in_flight until timer fires
            else:
                new_items = ev.get("items", [])
                commit(t, new_items, fid)
                # if still owed and no modification blocking, fetch again
                if owed and not active:
                    owed = False
                    emit_fetch(t)
        elif op == "advance":
            pass

        i += 1

    state = {
        "active": list(active),
        "owed": owed,
        "loading": loading,
        "placeholders": loading,
        "in_flight": in_flight,
        "retry_at": retry_at,
        "items": list(items),
    }

    return {
        "fetches": fetches,
        "commits": commits,
        "events": audit,
        "state": state,
    }
