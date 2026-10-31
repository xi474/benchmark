import random, sys, itertools, json
sys.path.insert(0,'/app/engines/calendar_windows')
from transform import transform

def brute(windows, cd):
    n=len(windows)
    best_val=None; best_list=None
    for mask in range(1<<n):
        sel=[windows[i] for i in range(n) if mask>>i&1]
        sel_sorted=sorted(sel,key=lambda x:(x[1],x[2],x[0]))
        ok=True
        for a,b in zip(sel_sorted, sel_sorted[1:]):
            if a[2]+cd > b[1]:
                ok=False;break
        if not ok: continue
        val=sum(w[3] for w in sel)
        ids=sorted(w[0] for w in sel)
        if best_val is None or val>best_val or (val==best_val and (ids<best_list)):
            best_val=val;best_list=ids
    if best_val is None:
        best_val=0;best_list=[]
    return {'selected':best_list,'value':best_val}

for t in range(10000):
    n=random.randint(0,8)
    windows=[]
    ids=set()
    for i in range(n):
        # unique ids
        while True:
            wid='w'+str(i)+''.join(random.choice('abc') for _ in range(random.randint(0,3)))
            if wid not in ids: break
        ids.add(wid)
        s=random.randint(0,10); e=random.randint(s+1,15)
        v=random.randint(-5,10)
        windows.append({'id':wid,'start':s,'end':e,'value':v})
    cd=random.randint(0,3)
    contract={'name':'calendar_windows','inputs':['x'],'cooldown':cd}
    got=transform([{'windows':windows}],contract)['result']
    exp=brute([(w['id'],w['start'],w['end'],w['value']) for w in windows],cd)
    if got!=exp:
        print('MISMATCH',windows,cd,got,exp)
        break
else:
    print('all ok')
