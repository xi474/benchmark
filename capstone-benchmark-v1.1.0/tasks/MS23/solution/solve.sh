#!/bin/bash
set -eu
cd /app
cat > solution.py <<'MEDIUM69_REFERENCE'
from collections import Counter
from functools import lru_cache
from itertools import product

def transform(p):
    def one(q):
        ab,bc,ac=(q[k] for k in ('ab','bc','ac'));n=len(ab);blocked=set(map(tuple,q['forbidden']))
        coords=list(product(range(n),repeat=3));size=len(coords)
        if any(sum(ab[a])!=sum(ac[a]) for a in range(n)):return None
        layers=[]
        for b in range(n):
            opts=[]
            def fill(i,rr,cc,vec):
                if i==n*n:
                    if not any(rr) and not any(cc):
                        v=tuple(vec)
                        score=sum(x*((sorted([a,b,c])[1]==n-1)-(sorted([a,b,c])[1]==0))
                                  for (a,c),x in zip(product(range(n),repeat=2),v))
                        opts.append((v,score))
                    return
                a,c=divmod(i,n)
                for x in range(1+(0 if (a,b,c) in blocked else min(rr[a],cc[c],ac[a][c]))):
                    if (c==n-1 and x!=rr[a]) or (a==n-1 and x!=cc[c]):continue
                    rr[a]-=x;cc[c]-=x;fill(i+1,rr,cc,vec+[x]);rr[a]+=x;cc[c]+=x
            fill(0,[r[b] for r in ab],list(bc[b]),[]);layers.append(opts)
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
        ans=dp(0,tuple(x for row in ac for x in row))
        if ans is None:return None
        d,m,w=ans
        sparse=lambda v:[list(k)+[x] for k,x in zip(coords,v) if x]
        return dict(tables=sum(d.values()),spectrum=[list(s) for s in sorted(d.items())],guaranteed=sparse(m),witness=sparse(w))
    return [one(q) for q in p['snapshots']]

from pathlib import Path
import json

def load_payload(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def build_component(input_path, output_path):
    value = transform(load_payload(input_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return value

MEDIUM69_REFERENCE
