import json
from pathlib import Path
import itertools


def load_payload(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    out = Path(output_path)
    if str(out.parent) not in ('', '.'):
        out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def _expand_bom(bom, sku, qty, acc):
    if sku not in bom:
        acc[sku] = acc.get(sku, 0) + qty
        return
    for child, cqty in bom[sku].items():
        _expand_bom(bom, child, qty * cqty, acc)


def transform(payload):
    run_id = payload['run_id']
    freeze = payload['freeze']
    changeover = payload['changeover']
    lines = payload['lines']
    bom = payload['bom']
    routing = payload['routing']
    substitutes = payload.get('substitutes', {})
    lots = payload['lots']
    orders = payload['orders']
    wip = payload['wip']

    wip_by_line = {}
    for w in wip:
        wip_by_line.setdefault(w['line'], []).append(w)

    line_min_start = {}
    for l in lines:
        ws = wip_by_line.get(l['id'], [])
        if ws:
            line_min_start[l['id']] = max(w['end'] for w in ws) + changeover
        else:
            line_min_start[l['id']] = freeze

    order_req = {}
    for o in orders:
        acc = {}
        _expand_bom(bom, o['sku'], o['qty'], acc)
        order_req[o['id']] = acc

    lots_by_material = {}
    for lot in lots:
        if lot['status'] == 'PASS':
            lots_by_material.setdefault(lot['material'], []).append(lot)

    def component_materials(component):
        return substitutes.get(component, [component])

    def order_duration(o):
        r = routing[o['sku']]
        return r['setup'] + r['per_unit'] * o['qty']

    def placements(o):
        dur = order_duration(o)
        res = []
        for l in lines:
            if o['sku'] not in l['qualified']:
                continue
            for (ws, we) in l['windows']:
                min_s = max(freeze, line_min_start[l['id']], ws)
                for s in range(min_s, we - dur + 2):
                    e = s + dur
                    if e > o['due'] or e > we:
                        break
                    res.append((l['id'], s, e))
        return res

    # Enumerate all feasible reservation allocations for a given assignment,
    # returning the lexicographically minimal alloc list (sorted by id, then
    # (component, lot, qty)). We search all allocations and keep the minimum.
    def best_reservation(assignment):
        demands = []
        for oid, (lid, s, e) in assignment.items():
            for comp, qty in order_req[oid].items():
                demands.append((oid, comp, qty, e))

        demand_candidates = []
        for (oid, comp, qty, e) in demands:
            cands = []
            for mat in component_materials(comp):
                for lot in lots_by_material.get(mat, []):
                    if lot['expiry'] >= e:
                        cands.append(lot)
            demand_candidates.append((oid, comp, qty, e, cands))

        remaining = {lot['id']: lot['qty'] for lot in lots if lot['status'] == 'PASS'}
        demand_candidates.sort(key=lambda d: len(d[4]))

        best_alloc = None
        best_alloc_list = None

        def alloc_list_value(alloc):
            items = []
            for oid in sorted(assignment.keys()):
                for (a, comp) in alloc:
                    if a == oid:
                        for (lot, q) in alloc[(a, comp)]:
                            items.append((oid, comp, lot, q))
            items.sort()
            return tuple(items)

        def backtrack(i):
            nonlocal best_alloc, best_alloc_list
            if i == len(demand_candidates):
                val = alloc_list_value(alloc)
                if best_alloc_list is None or val < best_alloc_list:
                    best_alloc_list = val
                    best_alloc = {k: list(v) for k, v in alloc.items()}
                return
            oid, comp, qty, e, cands = demand_candidates[i]
            cands_sorted = sorted(cands, key=lambda lot: (lot['id'],))

            def alloc_qty(idx, need):
                if need == 0:
                    backtrack(i + 1)
                    return
                if idx == len(cands_sorted):
                    return
                lot = cands_sorted[idx]
                avail = remaining[lot['id']]
                # try taking 0..min(avail, need) from this lot
                max_take = min(avail, need)
                for take in range(max_take, -1, -1):
                    if take > 0:
                        remaining[lot['id']] -= take
                        alloc.setdefault((oid, comp), []).append((lot['id'], take))
                    alloc_qty(idx + 1, need - take)
                    if take > 0:
                        remaining[lot['id']] += take
                        alloc[(oid, comp)].pop()
                        if not alloc[(oid, comp)]:
                            del alloc[(oid, comp)]

            alloc_qty(0, qty)

        alloc = {}
        backtrack(0)
        return best_alloc

    n = len(orders)
    order_list = sorted(orders, key=lambda o: (o['priority'], o['due'], o['id']))
    order_placements = {o['id']: placements(o) for o in orders}

    best = None

    for mask in range(1 << n):
        subset = [orders[i] for i in range(n) if mask & (1 << i)]
        if not subset:
            continue
        opts = [order_placements[o['id']] for o in subset]
        if any(len(o) == 0 for o in opts):
            continue
        for combo in itertools.product(*opts):
            assignment = {}
            line_tasks = {}
            ok = True
            for o, (lid, s, e) in zip(subset, combo):
                assignment[o['id']] = (lid, s, e)
                line_tasks.setdefault(lid, []).append((s, e, o['id']))
            for lid, tasks in line_tasks.items():
                all_tasks = [(w['start'], w['end'], w['id']) for w in wip_by_line.get(lid, [])]
                all_tasks += tasks
                all_tasks.sort()
                for i in range(len(all_tasks) - 1):
                    s1, e1, _ = all_tasks[i]
                    s2, e2, _ = all_tasks[i + 1]
                    if s2 < e1 + changeover:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue

            alloc = best_reservation(assignment)
            if alloc is None:
                continue

            p1 = sum(o['qty'] for o in subset if o['priority'] == 1)
            p2 = sum(o['qty'] for o in subset if o['priority'] == 2)
            p3 = sum(o['qty'] for o in subset if o['priority'] == 3)

            selected_ids = set(o['id'] for o in subset)
            comp_vec = tuple(1 if o['id'] in selected_ids else 0 for o in order_list)

            alloc_list = []
            for oid in sorted(assignment.keys()):
                lid, s, e = assignment[oid]
                items = []
                for (a, comp) in alloc:
                    if a == oid:
                        for (lot, q) in alloc[(a, comp)]:
                            items.append((comp, lot, q))
                items.sort()
                alloc_list.append((oid, lid, s, e, tuple(items)))

            candidate = {
                'subset': subset,
                'assignment': assignment,
                'alloc': alloc,
                'p': (p1, p2, p3),
                'comp_vec': comp_vec,
                'alloc_list': alloc_list,
            }
            if best is None:
                best = candidate
            else:
                if candidate['p'] > best['p']:
                    best = candidate
                elif candidate['p'] == best['p']:
                    if candidate['comp_vec'] > best['comp_vec']:
                        best = candidate
                    elif candidate['comp_vec'] == best['comp_vec']:
                        if candidate['alloc_list'] < best['alloc_list']:
                            best = candidate

    if best is None:
        return {
            'selected': [],
            'erp': {'run': {'id': run_id, 'freeze': freeze}, 'orders': []},
            'mes': [],
            'wms': [],
        }

    selected_ids = sorted(o['id'] for o in best['subset'])
    assignment = best['assignment']
    alloc = best['alloc']

    erp_orders = []
    for o in best['subset']:
        lid, s, e = assignment[o['id']]
        erp_orders.append({
            'wo': o['id'], 'run': run_id, 'sku': o['sku'], 'qty': o['qty'],
            'due': o['due'], 'start': s, 'end': e, 'line': lid,
            'status': 'PLANNED', 'parent': o['id'],
        })
    for w in wip:
        erp_orders.append({
            'wo': w['id'], 'run': run_id, 'sku': w['sku'], 'qty': w['qty'],
            'due': w['due'], 'start': w['start'], 'end': w['end'],
            'line': w['line'], 'status': 'WIP_CONT', 'parent': None,
        })
    erp_orders.sort(key=lambda x: x['wo'])

    mes = []
    line_tasks = {}
    for o in best['subset']:
        lid, s, e = assignment[o['id']]
        line_tasks.setdefault(lid, []).append((s, o['id'], o, 'PLANNED'))
    for w in wip:
        line_tasks.setdefault(w['line'], []).append((w['start'], w['id'], w, 'WIP_CONT'))
    for lid in sorted(line_tasks.keys()):
        tasks = sorted(line_tasks[lid], key=lambda t: (t[0], t[1]))
        for seq, (s, wid, o, status) in enumerate(tasks, 1):
            if status == 'PLANNED':
                _, _, e = assignment[o['id']]
                mes.append({
                    'run': run_id, 'line': lid, 'seq': seq, 'wo': o['id'],
                    'qty': o['qty'], 'start': s, 'end': e, 'status': 'PLANNED',
                })
            else:
                mes.append({
                    'run': run_id, 'line': lid, 'seq': seq, 'wo': w['id'],
                    'qty': w['qty'], 'start': w['start'], 'end': w['end'],
                    'status': 'WIP_CONT',
                })

    wms = []
    items = []
    for (oid, comp) in alloc:
        for (lot, q) in alloc[(oid, comp)]:
            if q > 0:
                items.append((oid, comp, lot, q))
    items.sort()
    for i, (oid, comp, lot, q) in enumerate(items, 1):
        wms.append({
            'reservation': 'r%04d' % i, 'run': run_id, 'wo': oid,
            'component': comp, 'lot': lot, 'qty': q, 'status': 'RESERVED',
        })

    return {
        'selected': selected_ids,
        'erp': {'run': {'id': run_id, 'freeze': freeze}, 'orders': erp_orders},
        'mes': mes,
        'wms': wms,
    }
