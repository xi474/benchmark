"""C011 integration: combine material demand and line windows into a rolling plan."""

import itertools


def combine(payload, left, right):
    run_id = payload.get("run_id", "run-0")
    freeze = payload.get("freeze", 0)
    changeover = payload.get("changeover", 0)
    orders = payload.get("orders", [])
    lines = payload.get("lines", [])
    wip = payload.get("wip", [])
    substitutes = payload.get("substitutes", {})
    lots = payload.get("lots", [])

    order_by_id = {o["id"]: o for o in orders}
    demand = left
    windows = right

    candidates = {}
    for oid, triples in windows.items():
        candidates[oid] = [(t[0], t[1], t[2]) for t in triples]

    wip_by_line = {}
    for w in wip:
        wip_by_line.setdefault(w["line"], []).append(w)

    def usable_lots(component, end):
        subs = substitutes.get(component, [component])
        result = []
        for lot in lots:
            if lot.get("status") != "PASS":
                continue
            if lot.get("expiry", 0) < end:
                continue
            if lot.get("material") not in subs:
                continue
            result.append(lot)
        return result

    def reserve(sel, placement):
        remaining = {lot["id"]: lot["qty"] for lot in lots}
        alloc = {}
        for oid in sel:
            _, _, end = placement[oid]
            comp_demand = demand.get(oid, {})
            oalloc = {}
            for comp, qty in sorted(comp_demand.items()):
                if qty <= 0:
                    continue
                need = qty
                usable = usable_lots(comp, end)
                usable.sort(key=lambda l: l["id"])
                chosen = []
                for lot in usable:
                    if need <= 0:
                        break
                    avail = remaining.get(lot["id"], 0)
                    take = min(need, avail)
                    if take > 0:
                        chosen.append((lot["id"], take))
                        remaining[lot["id"]] = avail - take
                        need -= take
                if need > 0:
                    return None
                oalloc[comp] = chosen
            alloc[oid] = oalloc
        return alloc

    def feasible_subset(selected_ids):
        sel = sorted(selected_ids, key=lambda oid: order_by_id[oid]["id"])
        placements_options = [candidates[oid] for oid in sel]
        if any(len(opts) == 0 for opts in placements_options):
            return None
        for combo in itertools.product(*placements_options):
            placement = dict(zip(sel, combo))
            line_tasks = {}
            for oid in sel:
                lid, s, e = placement[oid]
                line_tasks.setdefault(lid, []).append((s, e, oid))
            ok = True
            for lid, tasks in line_tasks.items():
                all_tasks = [(w["start"], w["end"], w["id"]) for w in wip_by_line.get(lid, [])]
                all_tasks += tasks
                all_tasks.sort(key=lambda t: t[0])
                for i in range(len(all_tasks) - 1):
                    if all_tasks[i][1] + changeover > all_tasks[i + 1][0]:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            alloc = reserve(sel, placement)
            if alloc is not None:
                return placement, alloc
        return None

    order_list = sorted(orders, key=lambda o: (o.get("priority", 0), o.get("due", 0), o["id"]))
    order_ids_sorted = sorted(o["id"] for o in orders)
    n = len(orders)

    best = None
    best_key = None

    for mask in range(1 << n):
        selected_ids = set()
        for i, oid in enumerate(order_ids_sorted):
            if mask & (1 << i):
                selected_ids.add(oid)
        if not selected_ids:
            continue
        result = feasible_subset(selected_ids)
        if result is None:
            continue
        placement, alloc = result

        p1 = sum(order_by_id[oid]["qty"] for oid in selected_ids if order_by_id[oid].get("priority", 0) == 1)
        p2 = sum(order_by_id[oid]["qty"] for oid in selected_ids if order_by_id[oid].get("priority", 0) == 2)
        p3 = sum(order_by_id[oid]["qty"] for oid in selected_ids if order_by_id[oid].get("priority", 0) == 3)
        comp_vec = tuple(1 if o["id"] in selected_ids else 0 for o in order_list)

        alloc_list = []
        for oid in sorted(selected_ids):
            lid, s, e = placement[oid]
            oalloc = alloc[oid]
            items = []
            for comp in sorted(oalloc):
                for lot, qty in sorted(oalloc[comp]):
                    items.append((comp, lot, qty))
            items.sort()
            alloc_list.append((oid, lid, s, e, tuple(items)))
        alloc_list.sort()

        key = (p1, p2, p3, comp_vec, tuple(alloc_list))
        if best_key is None:
            best_key = key
            best = (selected_ids, placement, alloc)
            continue
        a = key
        b = best_key
        if a[0] != b[0]:
            if a[0] > b[0]:
                best_key, best = key, (selected_ids, placement, alloc)
            continue
        if a[1] != b[1]:
            if a[1] > b[1]:
                best_key, best = key, (selected_ids, placement, alloc)
            continue
        if a[2] != b[2]:
            if a[2] > b[2]:
                best_key, best = key, (selected_ids, placement, alloc)
            continue
        if a[3] != b[3]:
            if a[3] > b[3]:
                best_key, best = key, (selected_ids, placement, alloc)
            continue
        if a[4] != b[4]:
            if a[4] < b[4]:
                best_key, best = key, (selected_ids, placement, alloc)
            continue

    if best is None:
        selected_ids, placement, alloc = set(), {}, {}
    else:
        selected_ids, placement, alloc = best

    selected = sorted(selected_ids)

    erp_orders = []
    for oid in selected:
        o = order_by_id[oid]
        lid, s, e = placement[oid]
        erp_orders.append({
            "wo": oid, "run": run_id, "sku": o["sku"], "qty": o["qty"],
            "due": o["due"], "start": s, "end": e, "line": lid,
            "status": "PLANNED", "parent": oid,
        })
    for w in wip:
        erp_orders.append({
            "wo": w["id"], "run": run_id, "sku": w["sku"], "qty": w["qty"],
            "due": w["due"], "start": w["start"], "end": w["end"],
            "line": w["line"], "status": "WIP_CONT", "parent": None,
        })
    erp_orders.sort(key=lambda x: x["wo"])

    mes = []
    line_tasks = {}
    for oid in selected:
        lid, s, e = placement[oid]
        o = order_by_id[oid]
        line_tasks.setdefault(lid, []).append((s, oid, o["qty"], e, "PLANNED"))
    for w in wip:
        line_tasks.setdefault(w["line"], []).append((w["start"], w["id"], w["qty"], w["end"], "WIP_CONT"))
    for lid in sorted(line_tasks):
        tasks = sorted(line_tasks[lid], key=lambda t: (t[0], t[1]))
        for seq, (s, wo, qty, e, status) in enumerate(tasks, start=1):
            mes.append({
                "run": run_id, "line": lid, "seq": seq, "wo": wo,
                "qty": qty, "start": s, "end": e, "status": status,
            })

    wms = []
    for oid in selected:
        oalloc = alloc.get(oid, {})
        for comp in sorted(oalloc):
            for lot, qty in sorted(oalloc[comp]):
                wms.append({
                    "reservation": None, "run": run_id, "wo": oid,
                    "component": comp, "lot": lot, "qty": qty, "status": "RESERVED",
                })
    wms.sort(key=lambda x: (x["wo"], x["component"], x["lot"], x["qty"]))
    for i, r in enumerate(wms, start=1):
        r["reservation"] = "r%04d" % i

    return {
        "selected": selected,
        "erp": {"run": {"id": run_id, "freeze": freeze}, "orders": erp_orders},
        "mes": mes,
        "wms": wms,
    }
