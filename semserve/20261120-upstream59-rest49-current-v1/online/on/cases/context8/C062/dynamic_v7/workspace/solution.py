"""C062 multi-backend snapshot polling close barrier."""

import json


def load_payload(input_path):
    with open(input_path, encoding="utf-8") as f:
        return json.load(f)


def transform(payload):
    events = payload["events"]
    out_events = []
    stores = {}

    def get_store(name):
        if name not in stores:
            stores[name] = {
                "backend": None,
                "state": "closed",
                "job": None,
                "revision": 0,
                "closed_at": None,
                "updates": 0,
            }
        return stores[name]

    for ev in events:
        time = ev["time"]
        store = ev["store"]
        op = ev["op"]
        st = get_store(store)

        if op == "open":
            st["backend"] = ev.get("backend")
            st["revision"] = ev.get("revision", 0)
            st["state"] = "open"
            out_events.append({"time": time, "store": store, "event": "opened"})

        elif op == "poll":
            if st["state"] == "open":
                if st["job"] is None:
                    st["job"] = ev["job"]
                    out_events.append(
                        {"time": time, "store": store, "event": "poll_started",
                         "job": ev["job"]}
                    )
                else:
                    out_events.append(
                        {"time": time, "store": store, "event": "poll_coalesced"}
                    )
            else:
                out_events.append(
                    {"time": time, "store": store, "event": "poll_rejected"}
                )

        elif op == "complete":
            job = ev["job"]
            changed = ev.get("changed", False)
            if st["state"] == "closing":
                # cancelled complete: no snapshot publish
                out_events.append(
                    {"time": time, "store": store, "event": "callback_cancelled",
                     "job": job}
                )
                st["job"] = None
                st["state"] = "closed"
                st["closed_at"] = time
                out_events.append(
                    {"time": time, "store": store, "event": "close_returned"}
                )
            else:
                if changed:
                    st["revision"] = ev["revision"]
                    st["updates"] += 1
                    out_events.append(
                        {"time": time, "store": store, "event": "snapshot_updated",
                         "job": job}
                    )
                else:
                    out_events.append(
                        {"time": time, "store": store, "event": "poll_unchanged",
                         "job": job}
                    )
                st["job"] = None

        elif op == "close":
            if st["state"] == "open":
                if st["job"] is None:
                    st["state"] = "closed"
                    st["closed_at"] = time
                    out_events.append(
                        {"time": time, "store": store, "event": "close_returned"}
                    )
                else:
                    st["state"] = "closing"
                    out_events.append(
                        {"time": time, "store": store, "event": "cancel_sent",
                         "job": st["job"]}
                    )
                    out_events.append(
                        {"time": time, "store": store, "event": "close_waiting"}
                    )
            elif st["state"] == "closing":
                out_events.append(
                    {"time": time, "store": store, "event": "close_waiting"}
                )
            else:  # closed
                out_events.append(
                    {"time": time, "store": store, "event": "close_returned"}
                )

    return {"events": out_events, "stores": stores}


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
