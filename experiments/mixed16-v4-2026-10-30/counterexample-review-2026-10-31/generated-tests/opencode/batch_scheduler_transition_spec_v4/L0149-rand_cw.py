import json, random, sys, importlib.util, itertools
from pathlib import Path
ROOT = Path('/app')

def load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

cw = load_mod('cw_transform', ROOT/'engines/calendar_windows/transform.py')
contract = {'name':'calendar_windows','operation':'weighted_intervals','cooldown':0}

def brute(windows, cooldown):
    n = len(windows)
    best = None
    for mask in range(1 << n):
        sel = [i for i in range(n) if mask & (1<<i)]
        ok = True
        for a in range(len(sel)):
            for b in range(a+1, len(sel)):
                i,j = sel[a], sel[b]
                e1=windows[i]['end']; s1=windows[i]['start']
                e2=windows[j]['end']; s2=windows[j]['start']
                if e1 <= e2:
                    if e1 + cooldown > s2: ok=False
                else:
                    if e2 + cooldown > s1: ok=False
                if not ok: break
            if not ok: break
        if not ok: continue
        val = sum(windows[i]['value'] for i in sel)
        ids = sorted(windows[i]['id'] for i in sel)
        cand=(val,ids)
        if best is None or cand[0]>best[0] or (cand[0]==best[0] and cand[1]<best[1]):
            best=cand
    return best

random.seed(1234)
for trial in range(20000):
    n = random.randint(0, 8)
    windows = []
    used = set()
    for i in range(n):
        while True:
            wid = 'w'+str(random.randint(0,30))
            if wid not in used:
                used.add(wid); break
        start = random.randint(0, 20)
        end = random.randint(start+1, 30)
        value = random.randint(-10, 10)
        windows.append({'id': wid, 'start': start, 'end': end, 'value': value})
    cooldown = random.randint(0, 5)
    c = dict(contract); c['cooldown'] = cooldown
    data = {'windows': windows}
    got = cw.transform([data], c)['result']
    exp = brute(windows, cooldown)
    exp = (exp[0], exp[1]) if exp else (0, [])
    if (got['value'], got['selected']) != exp:
        print('MISMATCH', trial, windows, cooldown)
        print('got', got, 'exp', exp)
        sys.exit(1)
print('RANDOM_CW_OK')
