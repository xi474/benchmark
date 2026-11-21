import json
from pathlib import Path


def load_payload(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def _job_profit(job, supplier, vehicle):
    return job['revenue'] - job['quantity'] * supplier['unit_cost'] - vehicle['cost'] * job['duration']


def transform(payload):
    vehicles = payload['vehicles']
    drivers = payload['drivers']
    suppliers = payload['suppliers']
    events = payload['events']
    rounds = payload['rounds']

    vmap = {v['id']: v for v in vehicles}
    dmap = {d['id']: d for d in drivers}
    smap = {s['id']: s for s in suppliers}

    committed = []
    committed_jobs = set()
    cancelled = set()
    ignored_cancellations = set()

    jobs = {}
    pending_jobs = set()

    sorted_events = sorted(events, key=lambda e: (e['visible'], e['id']))
    event_idx = 0

    results = []

    for rnd in rounds:
        cutoff = rnd['cutoff']
        commit = rnd['commit']

        while event_idx < len(sorted_events) and sorted_events[event_idx]['visible'] <= cutoff:
            ev = sorted_events[event_idx]
            event_idx += 1
            if ev['kind'] == 'request':
                job = ev['job']
                jobs[job['id']] = job
                pending_jobs.add(job['id'])
            elif ev['kind'] == 'cancel':
                jid = ev['job']
                committed_for_job = [a for a in committed if a['job'] == jid]
                if committed_for_job and committed_for_job[0]['start'] < cutoff:
                    ignored_cancellations.add(jid)
                else:
                    pending_jobs.discard(jid)
                    cancelled.add(jid)

        new_assignments = _optimize(
            jobs, pending_jobs, committed, committed_jobs,
            vmap, dmap, smap, cutoff
        )

        if commit:
            for a in new_assignments:
                committed.append(a)
                committed_jobs.add(a['job'])
                pending_jobs.discard(a['job'])

        all_assignments = list(committed) + list(new_assignments)
        all_assignments.sort(key=lambda a: (a['job'], a['start'], a['vehicle'], a['driver'], a['supplier']))

        total_profit = sum(a['profit'] for a in all_assignments)

        results.append({
            'cutoff': cutoff,
            'assignments': all_assignments,
            'profit': total_profit,
            'cancelled': sorted(cancelled),
            'ignored_cancellations': sorted(ignored_cancellations),
        })

    return {'rounds': results}


def _optimize(jobs, pending_jobs, committed, committed_jobs, vmap, dmap, smap, cutoff):
    candidates = {}

    for jid in pending_jobs:
        job = jobs[jid]
        cands = []
        for vid, veh in vmap.items():
            if veh['type'] != job['type']:
                continue
            if veh['capacity'] < job['quantity']:
                continue
            for did, drv in dmap.items():
                if veh['type'] not in drv['types']:
                    continue
                for sid in job['suppliers']:
                    sup = smap[sid]
                    start_min = max(cutoff, job['release'])
                    start_max = job['deadline'] - job['duration']
                    if start_max < start_min:
                        continue
                    for start in range(start_min, start_max + 1):
                        end = start + job['duration']
                        if start > sup['close']:
                            continue
                        if not _feasible(job, veh, drv, sup, start, end, committed, vmap, dmap, smap):
                            continue
                        profit = _job_profit(job, sup, veh)
                        cands.append({
                            'job': jid,
                            'vehicle': vid,
                            'driver': did,
                            'supplier': sid,
                            'start': start,
                            'end': end,
                            'quantity': job['quantity'],
                            'profit': profit,
                        })
        candidates[jid] = cands

    job_ids = sorted(pending_jobs)

    best = None
    best_key = None

    def rec(idx, chosen, total_profit):
        nonlocal best, best_key
        if idx == len(job_ids):
            if best is None:
                best = list(chosen)
                best_key = _key(chosen, total_profit)
            else:
                k = _key(chosen, total_profit)
                if k < best_key:
                    best = list(chosen)
                    best_key = k
            return
        jid = job_ids[idx]
        rec(idx + 1, chosen, total_profit)
        for cand in candidates[jid]:
            if _compatible(cand, chosen, vmap, dmap, smap):
                chosen.append(cand)
                rec(idx + 1, chosen, total_profit + cand['profit'])
                chosen.pop()

    rec(0, [], 0)

    return best if best is not None else []


def _key(chosen, total_profit):
    sorted_chosen = sorted(chosen, key=lambda a: (a['job'], a['start'], a['vehicle'], a['driver'], a['supplier']))
    tuples = [(a['job'], a['start'], a['vehicle'], a['driver'], a['supplier']) for a in sorted_chosen]
    return (-total_profit, -len(chosen), tuples)


def _compatible(cand, chosen, vmap, dmap, smap):
    for other in chosen:
        if cand['vehicle'] == other['vehicle']:
            if cand['start'] < other['end'] and other['start'] < cand['end']:
                return False
        if cand['driver'] == other['driver']:
            if cand['start'] < other['end'] and other['start'] < cand['end']:
                return False
    return True


def _feasible(job, veh, drv, sup, start, end, committed, vmap, dmap, smap):
    for a in committed:
        if a['vehicle'] == veh['id']:
            if start < a['end'] and a['start'] < end:
                return False
        if a['driver'] == drv['id']:
            if start < a['end'] and a['start'] < end:
                return False

    used = sum(a['quantity'] for a in committed if a['supplier'] == sup['id'])
    if used + job['quantity'] > sup['stock']:
        return False

    tasks = [a for a in committed if a['driver'] == drv['id']]
    tasks.append({'start': start, 'end': end})
    tasks.sort(key=lambda t: t['start'])

    total_work = sum(t['end'] - t['start'] for t in tasks)
    if total_work > drv['max_work']:
        return False

    continuous = 0
    prev_end = None
    for t in tasks:
        if prev_end is not None and t['start'] - prev_end >= drv['break']:
            continuous = 0
        continuous += t['end'] - t['start']
        if continuous > drv['max_continuous']:
            return False
        prev_end = t['end']

    return True
