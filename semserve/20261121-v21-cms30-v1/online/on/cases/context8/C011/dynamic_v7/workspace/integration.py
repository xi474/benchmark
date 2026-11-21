"""C011 integration: combine material demand and line windows into a rolling plan."""

import itertools


def combine(payload, left, right):
    """left = material demand {wo: {component: qty}}, right = line windows {wo: [[line,start,end],...]}."""
    run_id = payload.get("run_id")
    freeze = payload.get("freeze", 0)
    changeover = payload.get("changeover", 0)
    orders = payload.get("orders", [])
    wip = payload.get("wip", [])
    substitutes = payload.get("substitutes", {})
    lots = payload.get("lots", [])

    order_by_id = {o["id"]: o for o in orders}
    demand = left
    windows = right

    lots_by_material = {}
    for lot in lots:
        lots_by_material.setdefault(lot["material"], []).append(lot)

    placements = {}
    for oid, triples in windows.items():
        placements[oid] = [(t[0], t[1], t[2]) for t in triples]

    order_list = sorted(orders, key=lambda o: (o["priority"], o["due"], o["id"]))
    order_ids = [o["id"] for o in order_list]
    n = len(order_ids)
    priorities = sorted({o["priority"] for o in orders})

    def usable_lots(comp, end):
        subs = substitutes.get(comp, [comp])
        result = []
        for s in subs:
            for lot in lots_by_material.get(s, []):
                if lot["status"] == "PASS" and lot["expiry"] >= end:
                    result.append(lot)
        return result

    best_key = None
    best = None

    for mask in range(1 << n):
        selected_ids = [order_ids[i] for i in range(n) if (mask >> i) & 1]
        placement_lists = [placements[oid] for oid in selected_ids]
        if any(len(pl) == 0 for pl in placement_lists):
            continue

        for combo in itertools.product(*placement_lists):
            chosen = dict(zip(selected_ids, combo))

            line_tasks = {}
            for w in wip:
                line_tasks.setdefault(w["line"], []).append((w["start"], w["end"], w["id"], True))
            for oid in selected_ids:
                line, start, end = chosen[oid]
                line_tasks.setdefault(line, []).append((start, end, oid, False))

            ok = True
            for tasks in line_tasks.values():
                tasks_sorted = sorted(tasks, key=lambda t: (t[0], t[1]))
                prev_end = None
                for (s, e, tid, is_wip) in tasks_sorted:
                    if prev_end is not None and s < prev_end + changeover:
                        ok = False
                        break
                    prev_end = e
                if not ok:
                    break
            if not ok:
                continue

            reqs = []
            for oid in selected_ids:
                line, start, end = chosen[oid]
                for comp, qty in demand.get(oid, {}).items():
                    reqs.append((oid, comp, qty, end))
            reqs.sort(key=lambda r: (r[3], r[0], r[1]))

            lot_cap = {lot["id"]: lot["qty"] for lot in lots}
            feasible = True
            for (oid, comp, qty, end) in reqs:
                need = qty
                for lot in usable_lots(comp, end):
                    if need <= 0:
                        break
                    take = min(need, lot_cap.get(lot["id"], 0))
                    if take > 0:
                        lot_cap[lot["id"]] -= take
                        need -= take
                if need > 0:
                    feasible = False
                    break
            if not feasible:
                continue

            prio_qty = []
            for p in priorities:
                q = sum(order_by_id[oid]["qty"] for oid in selected_ids
                        if order_by_id[oid]["priority"] == p)
                prio_qty.append(q)

            comp_vec = tuple(1 if oid in chosen else 0 for oid in order_ids)

            lot_cap2 = {lot["id"]: lot["qty"] for lot in lots}
            per_order = {}
            for (oid, comp, qty, end) in reqs:
                need = qty
                for lot in usable_lots(comp, end):
                    if need <= 0:
                        break
                    take = min(need, lot_cap2.get(lot["id"], 0))
                    if take > 0:
                        lot_cap2[lot["id"]] -= take
                        need -= take
                        per_order.setdefault(oid, []).append((comp, lot["id"], take))

            id_list = []
            for oid in sorted(selected_ids):
                line, start, end = chosen[oid]
                a = tuple(sorted(per_order.get(oid, [])))
                id_list.append((oid, line, start, end, a))

            key = (tuple(prio_qty), comp_vec, tuple(id_list))

            if best_key is None or key > best_key:
                best_key = key
                best = (selected_ids, chosen, reqs)

    if best is None:
        selected_ids, chosen, reqs = [], {}, []
    else:
        selected_ids, chosen, reqs = best

    selected = sorted(selected_ids)

    erp_orders = []
    for w in wip:
        erp_orders.append({
            "wo": w["id"], "run": run_id, "sku": w["sku"], "qty": w["qty"],
            "due": w["due"], "start": w["start"], "end": w["end"],
            "line": w["line"], "status": "WIP_CONT", "parent": None,
        })
    for oid in selected_ids:
        o = order_by_id[oid]
        line, start, end = chosen[oid]
        erp_orders.append({
            "wo": oid, "run": run_id, "sku": o["sku"], "qty": o["qty"],
            "due": o["due"], "start": start, "end": end,
            "line": line, "status": "PLANNED", "parent": oid,
        })
    erp_orders.sort(key=lambda x: x["wo"])

    mes = []
    line_ids = sorted({w["line"] for w in wip} | {chosen[oid][0] for oid in selected_ids})
    for line in line_ids:
        tasks = []
        for w in wip:
            if w["line"] == line:
                tasks.append((w["start"], w["id"], "wip"))
        for oid in selected_ids:
            l, s, e = chosen[oid]
            if l == line:
                tasks.append((s, oid, "order"))
        tasks.sort(key=lambda t: (t[0], t[1]))
        for seq, (s, wid, kind) in enumerate(tasks, start=1):
            if kind == "wip":
                w = next(w for w in wip if w["id"] == wid)
                mes.append({
                    "run": run_id, "line": line, "seq": seq, "wo": wid,
                    "qty": w["qty"], "start": w["start"], "end": w["end"],
                    "status": "WIP_CONT",
                })
            else:
                o = order_by_id[wid]
                l, s, e = chosen[wid]
                mes.append({
                    "run": run_id, "line": line, "seq": seq, "wo": wid,
                    "qty": o["qty"], "start": s, "end": e, "status": "PLANNED",
                })

    lot_cap3 = {lot["id"]: lot["qty"] for lot in lots}
    per_order = {}
    for (oid, comp, qty, end) in reqs:
        need = qty
        for lot in usable_lots(comp, end):
            if need <= 0:
                break
            take = min(need, lot_cap3.get(lot["id"], 0))
            if take > 0:
                lot_cap3[lot["id"]] -= take
                need -= take
                per_order.setdefault(oid, []).append((comp, lot["id"], take))

    wms_rows = []
    for oid in selected_ids:
        for (comp, lot, qty) in sorted(per_order.get(oid, [])):
            wms_rows.append((oid, comp, lot, qty))
    wms_rows.sort()
    wms = []
    for i, (oid, comp, lot, qty) in enumerate(wms_rows, start=1):
        wms.append({
            "reservation": "r%04d" % i, "run": run_id, "wo": oid,
            "component": comp, "lot": lot, "qty": qty, "status": "RESERVED",
        })

    return {
        "selected": selected,
        "erp": {"run": {"id": run_id, "freeze": freeze}, "orders": erp_orders},
        "mes": mes,
        "wms": wms,
    }
