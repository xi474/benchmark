"""C009 partial-visibility irreversible transport scheduling.

combine(payload, left, right) consumes the two component business values:
  left  = business events sorted by (visible, event id)
  right = {vehicle_id: [driver_id, ...]} preserving declared driver order
and completes the remaining computation, returning {rounds: [...]}.
"""


def _sorted_events(events):
    return sorted(events, key=lambda e: (e["visible"], e["id"]))


def _job_profit(job, supplier, vehicle):
    return job["revenue"] - job["quantity"] * supplier["unit_cost"] - vehicle["cost"] * job["duration"]


def _feasible_assignments(job, vehicles, drivers, suppliers, crew, cutoff):
    out = []
    for vehicle in vehicles:
        if vehicle["type"] != job["type"]:
            continue
        if vehicle["capacity"] < job["quantity"]:
            continue
        for driver in drivers:
            if driver["id"] not in crew.get(vehicle["id"], []):
                continue
            for supplier in suppliers:
                if supplier["id"] not in job["suppliers"]:
                    continue
                if supplier["stock"] < job["quantity"]:
                    continue
                start_min = max(cutoff, job["release"])
                start_max = job["deadline"] - job["duration"]
                if start_max < start_min:
                    continue
                for start in range(start_min, start_max + 1):
                    end = start + job["duration"]
                    if start > supplier["close"]:
                        continue
                    out.append((vehicle, driver, supplier, start, end))
    return out


def _overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def _check_vehicle_driver(assignments, vehicle, driver, start, end):
    for a in assignments:
        if a["vehicle"] == vehicle["id"] and _overlap(a["start"], a["end"], start, end):
            return False
        if a["driver"] == driver["id"] and _overlap(a["start"], a["end"], start, end):
            return False
    return True


def _check_supplier(assignments, supplier, quantity):
    used = sum(a["quantity"] for a in assignments if a["supplier"] == supplier["id"])
    return used + quantity <= supplier["stock"]


def _check_driver_work(assignments, driver, start, end):
    tasks = [(a["start"], a["end"]) for a in assignments if a["driver"] == driver["id"]]
    tasks.append((start, end))
    tasks.sort()
    total = sum(e - s for s, e in tasks)
    if total > driver["max_work"]:
        return False
    continuous = 0
    prev_end = None
    for s, e in tasks:
        if prev_end is not None and s - prev_end >= driver["break"]:
            continuous = 0
        continuous += e - s
        if continuous > driver["max_continuous"]:
            return False
        prev_end = e
    return True


def _can_add(assignments, vehicle, driver, supplier, start, end, quantity):
    if not _check_vehicle_driver(assignments, vehicle, driver, start, end):
        return False
    if not _check_supplier(assignments, supplier, quantity):
        return False
    if not _check_driver_work(assignments, driver, start, end):
        return False
    return True


def _solve_round(jobs, vehicles, drivers, suppliers, crew, cutoff, committed):
    candidates = []
    for job in jobs:
        for (vehicle, driver, supplier, start, end) in _feasible_assignments(
                job, vehicles, drivers, suppliers, crew, cutoff):
            profit = _job_profit(job, supplier, vehicle)
            candidates.append({
                "job": job["id"],
                "vehicle": vehicle["id"],
                "driver": driver["id"],
                "supplier": supplier["id"],
                "start": start,
                "end": end,
                "quantity": job["quantity"],
                "profit": profit,
                "_vehicle": vehicle,
                "_driver": driver,
                "_supplier": supplier,
            })

    best = None
    best_score = None
    best_key = None
    n = len(candidates)
    for mask in range(1 << n):
        chosen = []
        seen_jobs = set()
        ok = True
        for i in range(n):
            if mask & (1 << i):
                c = candidates[i]
                if c["job"] in seen_jobs:
                    ok = False
                    break
                seen_jobs.add(c["job"])
                chosen.append(c)
        if not ok:
            continue
        assignments = list(committed)
        feasible = True
        for c in chosen:
            if not _can_add(assignments, c["_vehicle"], c["_driver"], c["_supplier"],
                            c["start"], c["end"], c["quantity"]):
                feasible = False
                break
            assignments.append({
                "job": c["job"], "vehicle": c["vehicle"], "driver": c["driver"],
                "supplier": c["supplier"], "start": c["start"], "end": c["end"],
                "quantity": c["quantity"], "profit": c["profit"],
            })
        if not feasible:
            continue
        total_profit = sum(c["profit"] for c in chosen)
        count = len(chosen)
        key_list = sorted(chosen, key=lambda c: (c["job"], c["start"], c["vehicle"],
                                                 c["driver"], c["supplier"]))
        key_tuple = tuple((c["job"], c["start"], c["vehicle"], c["driver"], c["supplier"])
                          for c in key_list)
        score = (total_profit, count)
        if best is None or score > best_score or (score == best_score and key_tuple < best_key):
            best = chosen
            best_score = score
            best_key = key_tuple

    if best is None:
        return []
    return [{k: c[k] for k in ("job", "vehicle", "driver", "supplier",
                               "start", "end", "quantity", "profit")} for c in best]


def combine(payload, left, right):
    vehicles = payload["vehicles"]
    drivers = payload["drivers"]
    suppliers = payload["suppliers"]
    events = _sorted_events(left)
    crew = right
    rounds = payload["rounds"]

    committed = []
    cancelled = []
    ignored_cancellations = []
    assigned_jobs = set()
    job_map = {}
    job_visible = {}
    processed_event_ids = set()

    result_rounds = []

    for rnd in rounds:
        cutoff = rnd["cutoff"]
        commit = rnd.get("commit", False)

        for e in events:
            if e["visible"] > cutoff:
                break
            if e["id"] in processed_event_ids:
                continue
            processed_event_ids.add(e["id"])
            if e["kind"] == "request":
                job = e["job"]
                job_map[job["id"]] = job
                job_visible[job["id"]] = e["visible"]
            elif e["kind"] == "cancel":
                jid = e["job"]
                committed_job = None
                for a in committed:
                    if a["job"] == jid:
                        committed_job = a
                        break
                if committed_job is not None and committed_job["start"] < cutoff:
                    ignored_cancellations.append(jid)
                else:
                    if committed_job is not None:
                        committed.remove(committed_job)
                    if jid in assigned_jobs:
                        assigned_jobs.discard(jid)
                    if jid not in cancelled:
                        cancelled.append(jid)

        available_jobs = []
        for jid, job in job_map.items():
            if job_visible[jid] <= cutoff and jid not in assigned_jobs and jid not in cancelled:
                available_jobs.append(job)

        new_assignments = _solve_round(available_jobs, vehicles, drivers, suppliers,
                                       crew, cutoff, committed)

        all_assignments = list(committed) + new_assignments
        all_assignments.sort(key=lambda a: (a["job"], a["start"], a["vehicle"],
                                            a["driver"], a["supplier"]))

        profit = sum(a["profit"] for a in all_assignments)

        result_rounds.append({
            "cutoff": cutoff,
            "assignments": [{k: a[k] for k in ("job", "vehicle", "driver", "supplier",
                                               "start", "end", "quantity", "profit")}
                            for a in all_assignments],
            "profit": profit,
            "cancelled": sorted(set(cancelled)),
            "ignored_cancellations": sorted(set(ignored_cancellations)),
        })

        if commit:
            committed = list(all_assignments)
            for a in new_assignments:
                assigned_jobs.add(a["job"])

    return {"rounds": result_rounds}
