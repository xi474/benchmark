import random
from bisect import bisect_right

def brute(parsed,cd):
    n=len(parsed); bv=None; bl=None
    for mask in range(1<<n):
        sel=[parsed[i] for i in range(n) if mask>>i&1]
        ss=sorted(sel,key=lambda x:(x[1],x[2],x[0]))
        ok=all(ss[i][2]+cd<=ss[i+1][1] for i in range(len(ss)-1))
        if not ok: continue
        v=sum(x[3] for x in sel); ids=sorted(x[0] for x in sel)
        if bv is None or v>bv or (v==bv and ids<bl): bv,bl=v,ids
    if bv is None: return [],0
    return bl,bv

def dp_lex(parsed,cd):
    ordered=sorted(parsed,key=lambda x:(x[2],x[1],x[0]))
    n=len(ordered); ends=[x[2] for x in ordered]
    vals=[0]*(n+1); lists=[()]*(n+1)
    for i in range(1,n+1):
        item=ordered[i-1]; p=bisect_right(ends,item[1]-cd)-1
        incv=item[3]+vals[p+1]
        incl=tuple(sorted(lists[p+1]+(item[0],)))
        # choose max val, tie lex min list
        no=(vals[i-1],lists[i-1]); inc=(incv,incl)
        if inc[0]>no[0] or (inc[0]==no[0] and inc[1]<no[1]):
            vals[i],lists[i]=inc
        else:
            vals[i],lists[i]=no
    return list(lists[n]),vals[n]

for t in range(20000):
    n=random.randint(0,9)
    parsed=[]
    for i in range(n):
        s=random.randint(0,10); e=random.randint(s+1,15); v=random.randint(-5,10)
        parsed.append((f'w{i}',s,e,v))
    cd=random.randint(0,3)
    b=brute(parsed,cd); d=dp_lex(parsed,cd)
    if b!=d:
        print('MISMATCH',parsed,cd,b,d)
        break
else:
    print('all ok')
