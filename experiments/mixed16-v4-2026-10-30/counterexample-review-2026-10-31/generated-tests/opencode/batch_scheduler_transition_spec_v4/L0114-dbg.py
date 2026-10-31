windows = [{'id': 'w8', 'start': 5, 'end': 11, 'value': 0}, {'id': 'w19', 'start': 0, 'end': 2, 'value': 0}, {'id': 'w24', 'start': 16, 'end': 22, 'value': 9}, {'id': 'w11', 'start': 14, 'end': 18, 'value': 3}]
cooldown = 0
n = len(windows)
cands = []
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
    cands.append((val, ids))
best = min((c for c in cands if c[0]==max(x[0] for x in cands)), key=lambda c: c[1])
print('all value-9 candidates:', [c for c in cands if c[0]==9])
print('best:', best)
