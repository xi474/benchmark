"""Conditional duration of successful absorption in a finite routing graph."""
from collections import defaultdict
from fractions import Fraction as F

def linear(matrix,values,independent):
    n=len(values);a=[list(row)+[y] for row,y in zip(matrix,values)]
    if independent:
        # Forward row elimination, followed by back substitution.
        for i in range(n):
            p=next(j for j in range(i,n) if a[j][i]);a[i],a[p]=a[p],a[i]
            for j in range(i+1,n):
                ratio=a[j][i]/a[i][i]
                for k in range(i,n+1):a[j][k]-=ratio*a[i][k]
        out=[F(0) for _ in values]
        for i in reversed(range(n)):out[i]=(a[i][-1]-sum(a[i][j]*out[j] for j in range(i+1,n)))/a[i][i]
        return out
    for i in range(n):
        p=next(j for j in range(i,n) if a[j][i]);a[i],a[p]=a[p],a[i]
        scale=a[i][i];a[i]=[x/scale for x in a[i]]
        for j in range(n):
            if i!=j and a[j][i]:
                scale=a[j][i];a[j]=[x-scale*y for x,y in zip(a[j],a[i])]
    return [r[-1] for r in a]

def solve(d,independent=False):
    nodes=d["stations"];good=set(d["delivered"]);routing=defaultdict(list)
    for e in d["routes"]:routing[e["from"]].append(e)
    live=set(good)
    while True:
        larger=live|{e["from"] for e in d["routes"] if e["to"] in live}
        if live==larger:break
        live=larger
    domain=sorted(live-good);index={n:i for i,n in enumerate(domain)}
    prob={k:F(k in good) for k in nodes}
    a=[[F(i==j) for j in range(len(domain))] for i in range(len(domain))]
    rhs=[F(0) for _ in domain];trans={}
    for m in domain:
        total=sum(e["weight"] for e in routing[m])
        trans[m]=[(e["to"],F(e["weight"],total),e["time"]) for e in routing[m]]
        for v,p,_ in trans[m]:
            if v in index:a[index[m]][index[v]]-=p
            elif v in good:rhs[index[m]]+=p
    prob.update(zip(domain,linear(a,rhs,independent)))
    if independent:
        # On successful paths, the conditional transition probability is
        # P(i,j) p(j)/p(i). Solve directly for their expected durations.
        b=[[F(i==j) for j in range(len(domain))] for i in range(len(domain))]
        rhs=[F(0) for _ in domain]
        for m in domain:
            for v,p,t in trans[m]:
                q=p*prob[v]/prob[m]
                if v in index:b[index[m]][index[v]]-=q
                rhs[index[m]]+=q*t
        conditional=dict(zip(domain,linear(b,rhs,True)))
    else:
        rhs=[sum(p*t*prob[v] for v,p,t in trans[m]) for m in domain]
        conditional={m:t/prob[m] for m,t in zip(domain,linear(a,rhs,False))}
    def fmt(v):return [v.numerator,v.denominator]
    return {"stations":{k:{"success":fmt(prob[k]),"mean_if_success":fmt(conditional.get(k,F(0))) if prob[k] else None} for k in nodes}}
