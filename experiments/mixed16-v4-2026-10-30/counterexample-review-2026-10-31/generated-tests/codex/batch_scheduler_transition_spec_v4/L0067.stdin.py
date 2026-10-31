import random, sys
sys.path.insert(0,'/app/engines/calendar_windows')
from transform import transform

def brute(parsed, cd):
    n=len(parsed)
    best_val=None; best_list=None
    for mask in range(1<<n):
        sel=[parsed[i] for i in range(n) if mask>>i&1]
        ss=sorted(sel,key=lambda x:(x[1],x[2],x[0]))
        ok=True
        for a,b in zip(ss,ss[1:]):
            if a[2]+cd > b[1]: ok=False;break
        if not ok: continue
        val=sum(w[3] for w in sel)
        ids=sorted(w[0] for w in sel)
        if best_val is None or val>best_val or (val==best_val and ids<best_list):
            best_val=val;best_list=ids
    if best_val is None:
        best_val=0;best_list=[]
    return {'selected':best_list,'value':best_val}

for t in range(100000):
    n=random.randint(0,10)
    windows=[]; used=set()
    for i in range(n):
        wid=f'w{i}'
        if wid in used: wid=f'w{i}_{t}'
        used.add(wid)
        s=random.randint(0,12); e=random.randint(s+1,18)
        v=random.randint(-8,12)
        windows.append({'id':wid,'start':s,'end':e,'value':v})
    cd=random.randint(0,4)
    contract={'name':'calendar_windows','inputs':['x'],'cooldown':cd}
    got=transform([{'windows':windows}],contract)['result']
    exp=brute([(w['id'],w['start'],w['end'],w['value']) for w in windows],cd)
    if got!=exp:
        print('MISMATCH',windows,cd,got,exp)
        break
else:
    print('all ok')
