from pathlib import Path
import json
from collections import deque


def _domain_state_at(domain, t, timeline):
    """State of a domain at integer slot t given its sorted timeline.

    timeline: list of (effective_time, record_time, state) filtered to
    record_time <= as_of and sorted by (effective_time, record_time).
    """
    state = "up"
    for eff, rec, st in timeline:
        if eff > t:
            break
        state = st
    return state


def _build_timelines(payload, as_of):
    domains = payload["domains"]
    timelines = {d: [] for d in domains}
    for dom, eff, rec, st in payload["log"]:
        if rec <= as_of:
            timelines[dom].append((eff, rec, st))
    for d in domains:
        timelines[d].sort(key=lambda x: (x[0], x[1]))
    return timelines


def _topo_order(services):
    service_ids = [s["id"] for s in services]
    service_map = {s["id"]: s for s in services}
    indeg = {sid: 0 for sid in service_ids}
    children = {sid: [] for sid in service_ids}
    for s in services:
        for inp in s["inputs"]:
            if inp in service_map:
                indeg[s["id"]] += 1
                children[inp].append(s["id"])
    q = deque([sid for sid in service_ids if indeg[sid] == 0])
    order = []
    while q:
        sid = q.popleft()
        order.append(sid)
        for c in children[sid]:
            indeg[c] -= 1
            if indeg[c] == 0:
                q.append(c)
    return order, service_map


def _compute_availability(payload, as_of, start, end):
    """Map each domain/service id -> list of bool (available per slot)."""
    domains = payload["domains"]
    services = payload["services"]
    timelines = _build_timelines(payload, as_of)

    avail = {}
    for d in domains:
        tl = timelines[d]
        avail[d] = [_domain_state_at(d, t, tl) == "up" for t in range(start, end)]

    order, service_map = _topo_order(services)
    for sid in order:
        s = service_map[sid]
        need = s["need"]
        inputs = s["inputs"]
        res = []
        for t in range(start, end):
            cnt = 0
            for inp in inputs:
                if avail[inp][t - start]:
                    cnt += 1
            res.append(cnt >= need)
        avail[sid] = res
    return avail


def _incidents_for_target(target, avail, start, end):
    slots = avail[target]
    incidents = []
    i = start
    while i < end:
        if not slots[i - start]:
            j = i
            while j < end and not slots[j - start]:
                j += 1
            incidents.append([target, i, j])
            i = j
        else:
            i += 1
    return incidents


def _slot_avail_with(payload, as_of, t, targets, forced, timelines, order, service_map):
    """Availability of all targets at slot t with forced domains up."""
    domains = payload["domains"]
    forced = set(forced)
    avail = {}
    for d in domains:
        if d in forced:
            avail[d] = True
        else:
            avail[d] = _domain_state_at(d, t, timelines[d]) == "up"
    for sid in order:
        s = service_map[sid]
        cnt = sum(1 for inp in s["inputs"] if avail[inp])
        avail[sid] = cnt >= s["need"]
    return all(avail[g] for g in targets)


def _minimal_repairs(payload, as_of, start, end, targets):
    domains = payload["domains"]
    services = payload["services"]
    timelines = _build_timelines(payload, as_of)
    order, service_map = _topo_order(services)

    base_avail = _compute_availability(payload, as_of, start, end)
    all_ok = all(all(base_avail[g][t - start] for g in targets)
                 for t in range(start, end))
    if all_ok:
        return [[]]

    # relevant domains: broken in at least one slot
    relevant = [d for d in domains
                if any(_domain_state_at(d, t, timelines[d]) != "up"
                       for t in range(start, end))]

    # per-slot minimal fix sets (only for bad slots)
    slot_fix_sets = []
    for t in range(start, end):
        bad = any(not base_avail[g][t - start] for g in targets)
        if not bad:
            continue
        broken_here = [d for d in relevant
                       if _domain_state_at(d, t, timelines[d]) != "up"]
        fixes = _minimal_fix_sets_for_slot(
            payload, as_of, t, targets, broken_here, timelines, order, service_map)
        slot_fix_sets.append(fixes)

    # find minimal hitting sets: union of one fix set per slot
    results = set()

    def search(idx, chosen):
        if idx == len(slot_fix_sets):
            results.add(frozenset(chosen))
            return
        for fix in slot_fix_sets[idx]:
            search(idx + 1, chosen | fix)

    search(0, frozenset())

    result_sets = list(results)
    minimal = [s for s in result_sets
               if not any(other < s for other in result_sets)]
    minimal.sort(key=lambda s: (len(s), sorted(s)))
    return [sorted(s) for s in minimal]


def _minimal_fix_sets_for_slot(payload, as_of, t, targets, broken_here,
                               timelines, order, service_map):
    """Minimal subsets of broken_here that fix slot t (all targets available)."""
    def ok(chosen):
        return _slot_avail_with(payload, as_of, t, targets, chosen,
                                timelines, order, service_map)

    if ok(set()):
        return [frozenset()]

    n = len(broken_here)
    found = []

    def rec(i, chosen):
        if ok(chosen):
            found.append(frozenset(chosen))
            return
        if i == n:
            return
        rec(i + 1, chosen | {broken_here[i]})
        rec(i + 1, chosen)

    rec(0, set())

    minimal = [s for s in found if not any(other < s for other in found)]
    return minimal


def transform(payload):
    out = []
    for q in payload["queries"]:
        as_of = q["as_of"]
        start = q["start"]
        end = q["end"]
        targets = q["targets"]

        avail = _compute_availability(payload, as_of, start, end)

        incidents = []
        for target in targets:
            incidents.extend(_incidents_for_target(target, avail, start, end))
        incidents.sort(key=lambda x: (x[0], x[1]))

        repairs = _minimal_repairs(payload, as_of, start, end, targets)

        out.append({"incidents": incidents, "repairs": repairs})
    return out


def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value
