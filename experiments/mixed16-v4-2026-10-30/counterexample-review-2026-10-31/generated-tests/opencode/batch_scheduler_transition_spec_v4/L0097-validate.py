import json, sys, itertools
from pathlib import Path
sys.path.insert(0, '/app/engines/calendar_windows')
sys.path.insert(0, '/app/engines/worker_assignment')
sys.path.insert(0, '/app/engines/job_order')
from transform import transform as cw_transform
from transform import transform as wa_transform
from transform import transform as jo_transform

ROOT = Path('/app')

# ---- calendar_windows brute force ----
cw_contract = json.loads((ROOT/'engines/calendar_windows/contract.json').read_text())
cw_data = json.loads((ROOT/'inputs/calendar_windows.json').read_text())
windows = cw_data['windows']
cooldown = cw_contract['cooldown']

# normalize ids (strip) for brute force
norm = [{'id': w['id'].strip(), 'start': w['start'], 'end': w['end'], 'value': w['value']} for w in windows]
n = len(norm)
best = None
for mask in range(1 << n):
    sel = [i for i in range(n) if mask & (1 << i)]
    # check compatibility pairwise
    ok = True
    for a in range(len(sel)):
        for b in range(a+1, len(sel)):
            i, j = sel[a], sel[b]
            e1 = norm[i]['end']; s1 = norm[i]['start']
            e2 = norm[j]['end']; s2 = norm[j]['start']
            # earlier by end; if same end not compatible regardless
            if e1 <= e2:
                if e1 + cooldown > s2: ok = False
            else:
                if e2 + cooldown > s1: ok = False
            if not ok: break
        if not ok: break
    if not ok: continue
    val = sum(norm[i]['value'] for i in sel)
    ids = sorted(norm[i]['id'] for i in sel)
    cand = (val, ids)
    if best is None:
        best = cand
    else:
        if cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
            best = cand

got = cw_transform([cw_data], cw_contract)['result']
print('CW brute:', best)
print('CW dp:   ', (got['value'], got['selected']))
assert (got['value'], got['selected']) == best, 'calendar_windows MISMATCH'

# ---- worker_assignment brute force ----
wa_contract = json.loads((ROOT/'engines/worker_assignment/contract.json').read_text())
wa_data = json.loads((ROOT/'inputs/worker_assignment.json').read_text())
cw_out = cw_transform([cw_data], cw_contract)  # full wrapper

got_wa = wa_transform([wa_data, cw_out], wa_contract)['result']

# replicate selected filter
sel_set = set(cw_out['result']['selected'])
workers = [w for w in wa_data['workers'] if w['id'] in sel_set]
jobs = wa_data['jobs']
jobs_sorted = sorted(jobs, key=lambda j: j['id'])
W = len(workers)
caps = [w['capacity'] for w in workers]
skills = [set(w['skills']) for w in workers]
aff = [w['affinity'] for w in workers]
costs = [w['cost'] for w in workers]
wids = [w['id'] for w in workers]
durs = [j['duration'] for j in jobs_sorted]
js = [j['skill'] for j in jobs_sorted]
jids = [j['id'] for j in jobs_sorted]

best_wa = None
for combo in itertools.product(range(W), repeat=len(jobs_sorted)):
    used = [0]*W
    ok = True
    for i, w in enumerate(combo):
        if js[i] not in skills[w]: ok=False; break
        used[w] += durs[i]
        if used[w] > caps[w]: ok=False; break
    if not ok: continue
    sc = sum(aff[w].get(jids[i], 0) for i, w in enumerate(combo))
    co = sum(costs[w]*durs[i] for i, w in enumerate(combo))
    seq = [wids[w] for w in combo]
    cand = (sc, co, seq)
    if best_wa is None or (cand[0] > best_wa[0] or (cand[0]==best_wa[0] and (cand[1] < best_wa[1] or (cand[1]==best_wa[1] and cand[2] < best_wa[2])))):
        best_wa = cand

print('WA brute:', best_wa)
print('WA got:  ', (got_wa['score'], got_wa['cost'], [a['worker'] for a in got_wa['assignments']]))
if best_wa is None:
    assert got_wa['feasible'] is False
else:
    assert got_wa['feasible'] is True
    assert (got_wa['score'], got_wa['cost'], [a['worker'] for a in got_wa['assignments']]) == best_wa, 'worker_assignment MISMATCH'

# ---- job_order sample ----
jo_contract = json.loads((ROOT/'engines/job_order/contract.json').read_text())
jo_data = json.loads((ROOT/'inputs/job_order.json').read_text())
got_jo = jo_transform([jo_data], jo_contract)['result']
print('JO:', got_jo)
assert got_jo['makespan'] == 11
assert got_jo['critical_path'] == ['j0','j2','j4']
assert got_jo['waves'] == [['j0','j1'],['j2','j3'],['j4','j5']]
assert got_jo['earliest_finish'] == {'j0':5,'j1':1,'j2':7,'j3':4,'j4':11,'j5':9}

print('ALL_BRUTE_FORCE_CHECKS_PASSED')
