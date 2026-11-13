from collections import defaultdict
from fractions import Fraction as F

def solve(d,independent=False):
    # Reachability partitions the small plant into recurrent components.
    stations=d["stations"];edges=d["transitions"];out=defaultdict(list)
    for e in edges:out[e["from"]].append((e["to"],e["gain"]))
    reach={}
    for start in stations:
        seen={start};pending=[start]
        while pending:
            for n,_ in out[pending.pop()]:
                if n not in seen:seen.add(n);pending.append(n)
        reach[start]=seen
    if independent:
        cycles=[]
        def visit(start,n,seen,total):
            for m,gain in out[n]:
                if m==start:cycles.append((start,F(total+gain,len(seen))))
                elif m>start and m not in seen:visit(start,m,seen|{m},total+gain)
        for n in stations:visit(n,n,{n},0)
    else:
        cycles=[];remaining=set(stations)
        while remaining:
            seed=min(remaining);group={n for n in reach[seed] if seed in reach[n]}
            remaining-=group;n=len(group)
            local=[e for e in edges if e["from"] in group and e["to"] in group]
            if not local:continue
            # Karp's maximum cycle mean with a zero-cost artificial source.
            table=[dict.fromkeys(group,0)]
            for k in range(n):
                row={}
                for e in local:
                    u,v=e["from"],e["to"];candidate=table[-1][u]+e["gain"]
                    if v not in row or candidate>row[v]:row[v]=candidate
                table.append(row)
            mean=max(min(F(table[n][v]-table[k][v],n-k) for k in range(n)) for v in group)
            cycles.append((seed,mean))
    result={}
    for n in stations:
        best=max((m for s,m in cycles if s in reach[n]),default=None)
        result[n]=[best.numerator,best.denominator] if best is not None else None
    return {"sustainable":result}
