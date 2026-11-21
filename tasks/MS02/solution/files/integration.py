from functools import lru_cache


def combine(payload, left, right):
    p=payload; topics=p["topics"]; papers=sorted(p["papers"],key=lambda r:r["id"])
    if not topics:
        return {"review":[],"graph":[list(e) for e in right]}
    idx={r['id']:j for j,r in enumerate(papers)}
    offers=[{idx[k]:v for k,v in row.items()} for row in left]
    def assign(floor):
        @lru_cache(None)
        def step(t,used):
            if t==len(topics):return 0,()
            out=[]
            for j,q in offers[t].items():
                if q<floor or used&(1<<j):continue
                tail=step(t+1,used|(1<<j))
                if tail is not None:out.append((tail[0]-q,(j,)+tail[1]))
            return min(out) if out else None
        return step(0,0)
    for floor in sorted({q for row in offers for q in row.values()},reverse=True):
        plan=assign(floor)
        if plan is not None:
            rows=[[topics[i],papers[j]["id"],offers[i][j]] for i,j in enumerate(plan[1])]
            edges={tuple(e) for e in right}|{(paper,"supports",t) for t,paper,q in rows}
            return {"review":rows,"graph":[list(e) for e in sorted(edges)]}
    return None

from pathlib import Path
import json

