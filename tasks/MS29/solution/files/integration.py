from collections import deque
from itertools import combinations,product

def combine(p, left, right):
    dishes=sorted(r for r in p['dishes'] if r[2]<=p['max_difficulty'])
    offers=sorted(p['offers']);ops=sorted(p['prep'])
    items=sorted(set(p['stock']).union(*(set(d[3]) for d in dishes),*(set(v[1]) for v in offers),
                                      *(set(o[1])|set(o[2]) for o in ops)))
    def vec(d):return tuple(d.get(i,0) for i in items)
    cases=[(ids,vec(needs)) for ids,needs in left]
    found={};baskets=right
    for cost,n,q in baskets:
        remaining=[(tuple(k),needs) for k,needs in cases if tuple(k) not in found]
        if not remaining:break
        start=tuple(p['stock'].get(i,0)+sum(count*offer[1].get(i,0) for count,offer in zip(q,offers)) for i in items)
        queue=deque([(start,(0,)*len(ops),())]);visited={(0,)*len(ops)}
        while queue and remaining:
            stock,used,path=queue.popleft();unsolved=[]
            for ds,needs in remaining:
                if all(a>=b for a,b in zip(stock,needs)):
                    found[ds]=dict(cost=cost,buy=list(q),steps=list(path),left={k:a-b for k,a,b in zip(items,stock,needs) if a>b})
                else:unsolved.append((ds,needs))
            remaining=unsolved
            for j,(k,take,give,limit) in enumerate(ops):
                if used[j]>=limit or any(a<b for a,b in zip(stock,vec(take))):continue
                nxt=used[:j]+(used[j]+1,)+used[j+1:]
                if nxt in visited:continue
                visited.add(nxt)
                new=tuple(a-b+c for a,b,c in zip(stock,vec(take),vec(give)))
                queue.append((new,nxt,path+(k,)))
    return [dict(dishes=ds,plan=found.get(tuple(ds))) for ds,needs in cases]

from pathlib import Path
import json

