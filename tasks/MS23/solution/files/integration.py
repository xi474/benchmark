from collections import Counter
from functools import lru_cache
from itertools import product

def combine(p, left, right):
    def one(i,q):
        ab,bc,ac=(q[k] for k in ('ab','bc','ac'));n=len(ab);blocked=set(map(tuple,q['forbidden']))
        coords=list(product(range(n),repeat=3));size=len(coords)
        if not left[i][0]:return None
        layers=right[i]
        @lru_cache(None)
        def dp(b,res):
            if b==n:return ({0:1},(0,)*size,(0,)*size) if not any(res) else None
            counts=Counter();mins=None;wscore=None;witness=None
            for layer,score in layers[b]:
                left=tuple(r-x for r,x in zip(res,layer))
                if min(left)<0:continue
                sub=dp(b+1,left)
                if sub is None:continue
                dist,mn,win=sub
                counts.update({t+score:v for t,v in dist.items()})
                add=tuple(layer[a*n+c] if j==b else 0 for a,j,c in coords)
                merged=tuple(x+y for x,y in zip(mn,add));mins=merged if mins is None else tuple(map(min,zip(mins,merged)))
                weight=min(dist)+score;candidate=tuple(x+y for x,y in zip(win,add))
                if wscore is None or (weight,candidate)<(wscore,witness):wscore,witness=weight,candidate
            return (counts,mins,witness) if counts else None
        ans=dp(0,tuple(left[i][1]))
        if ans is None:return None
        d,m,w=ans
        sparse=lambda v:[list(k)+[x] for k,x in zip(coords,v) if x]
        return dict(tables=sum(d.values()),spectrum=[list(s) for s in sorted(d.items())],guaranteed=sparse(m),witness=sparse(w))
    return [one(i,q) for i,q in enumerate(p['snapshots'])]

from pathlib import Path
import json

