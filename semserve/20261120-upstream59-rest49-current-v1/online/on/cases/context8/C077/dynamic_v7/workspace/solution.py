"""Implement the public business contract in TASK.md."""

import json


def transform(payload):
    events = payload["events"]

    fetches = []
    commits = []
    audit = []

    active = []          # sorted list of active modification ids
    owed = False         # pending refresh obligation
    loading = False      # pending request / retry / refresh
    in_flight = None     # current network request id
    retry_at = None      # scheduled retry time
    items = []           # committed items

    fetch_counter = 0

    def state():
        return {
            "active": list(active),
            "owed": owed,
            "loading": loading,
            "placeholders": loading,
            "in_flight": in_flight,
            "retry_at": retry_at,
            "items": list(items),
        }

    def do_fetch(time):
        nonlocal fetch_counter, in_flight, loading
        fetch_counter += 1
        fid = "fetch-%d" % fetch_counter
        fetches.append({"id": fid, "time": time})
        audit.append({"time": time, "event": "fetch", "id": fid})
        in_flight = fid
        loading = True

    def commit(time, fid, new_items):
        nonlocal items
        items.extend(new_items)
        commits.append({"time": time, "items": list(new_items)})
        audit.append({"time": time, "event": "committed", "id": fid})

    for ev in events:
        time = ev["time"]
        op = ev["op"]

        # Timers fire before external events at the same time.
        if retry_at is not None and time >= retry_at:
            retry_at = None
            in_flight = None
            if active:
                # modification still in flight: keep obligation, retry on finish
                owed = True
            else:
                do_fetch(time)

        if op == "start":
            active.append(ev["id"])
            active.sort()
            audit.append({"time": time, "event": "modification_started",
                          "id": ev["id"]})
        elif op == "finish":
            active.remove(ev["id"])
            audit.append({"time": time, "event": "modification_finished",
                          "id": ev["id"]})
            owed = True
            # If no active modification remains and no request/retry pending,
            # fetch now (same processing).
            if not active and in_flight is None and retry_at is None:
                do_fetch(time)
        elif op == "refresh":
            owed = True
            if not active and in_flight is None and retry_at is None:
                do_fetch(time)
        elif op == "response":
            fid = ev["id"]
            if "items" in ev:
                # success
                commit(time, fid, ev["items"])
                in_flight = None
                if owed and not active:
                    owed = False
                    do_fetch(time)
                else:
                    loading = False
            elif ev.get("failed"):
                # failure: no commit, schedule retry
                in_flight = None
                retry_at = time + 2000
                audit.append({"time": time, "event": "retry_scheduled",
                              "due": retry_at, "reason": "failure"})
                loading = True
            elif ev.get("stale") == 1:
                # stale: no commit, keep in_flight, schedule retry
                retry_at = time + 1000
                audit.append({"time": time, "event": "retry_scheduled",
                              "due": retry_at, "reason": "stale"})
                loading = True
        elif op == "advance":
            pass

    return {
        "fetches": fetches,
        "commits": commits,
        "events": audit,
        "state": state(),
    }


def load_payload(input_path):
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
