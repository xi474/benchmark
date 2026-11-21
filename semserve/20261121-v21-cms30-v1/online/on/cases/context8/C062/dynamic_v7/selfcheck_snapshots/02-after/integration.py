def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    events = payload["events"]

    # left: initial store state keyed by original open-event position (decimal string).
    # right: per-complete-event effect keyed by original position (decimal string).
    stores = {}
    for key, init in left.items():
        stores[key] = dict(init)

    # Map store name -> open-event position key, and reverse.
    store_key = {}
    key_store = {}
    for index, ev in enumerate(events):
        if ev.get("op") == "open":
            store_key[ev["store"]] = str(index)
            key_store[str(index)] = ev["store"]

    audit = []

    def emit(time, store, event, job=None):
        rec = {"time": time, "store": store, "event": event}
        if job is not None:
            rec["job"] = job
        audit.append(rec)

    in_flight = {}  # store -> job name
    closing = set()  # stores currently closing (waiting on barrier)

    for index, ev in enumerate(events):
        op = ev["op"]
        store = ev["store"]
        time = ev["time"]

        if op == "open":
            key = str(index)
            st = stores[key]
            st["state"] = "open"
            emit(time, store, "opened")
            continue

        if op == "poll":
            key = store_key[store]
            st = stores[key]
            if st["state"] == "open":
                if st["job"] is None:
                    st["job"] = ev["job"]
                    in_flight[store] = ev["job"]
                    emit(time, store, "poll_started", ev["job"])
                else:
                    emit(time, store, "poll_coalesced")
            else:
                emit(time, store, "poll_rejected")
            continue

        if op == "complete":
            job = ev["job"]
            key = store_key[store]
            st = stores[key]
            changed = bool(ev.get("changed", False))
            cancelled = store in closing
            if cancelled:
                emit(time, store, "callback_cancelled", job)
                closing.discard(store)
                st["job"] = None
                st["state"] = "closed"
                st["closed_at"] = time
                emit(time, store, "close_returned")
            else:
                if changed:
                    st["revision"] = ev["revision"]
                    st["updates"] += 1
                    emit(time, store, "snapshot_updated", job)
                else:
                    emit(time, store, "poll_unchanged", job)
                st["job"] = None
                in_flight.pop(store, None)
            continue

        if op == "close":
            key = store_key[store]
            st = stores[key]
            if st["state"] == "closed":
                emit(time, store, "close_returned")
                continue
            if st["state"] == "closing":
                emit(time, store, "close_waiting")
                continue
            # state == "open"
            if st["job"] is None:
                st["state"] = "closed"
                st["closed_at"] = time
                emit(time, store, "close_returned")
            else:
                st["state"] = "closing"
                closing.add(store)
                emit(time, store, "cancel_sent", st["job"])
                emit(time, store, "close_waiting")

    final_stores = {}
    for key, st in stores.items():
        final_stores[key_store[key]] = st

    return {"events": audit, "stores": final_stores}
