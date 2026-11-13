"""Compressed planar zones and an independent unit-cell reference."""
from collections import Counter
from functools import reduce
from heapq import heappop,heappush
from math import gcd

def solve(d,independent=False):
    width,height=d["size"];start=d["entry"]
    xs={0,width};ys={0,height}
    for x,y,u,v in d["blocked"]+[w["segment"] for w in d["walls"]]:
        xs.update((x,u));ys.update((y,v))
    if independent:
        # Registered large maps are exact magnifications of smaller plans.
        # A uniform-cost cell reference can sweep lattice squares after scaling.
        scale=reduce(gcd,(*xs,*ys))
        X=range(0,width+1,scale);Y=range(0,height+1,scale)
    else:
        X=sorted(xs);Y=sorted(ys)
    w=len(X)-1;h=len(Y)-1
    free={(i,j) for i in range(w) for j in range(h) if not any(x<=X[i]<u and y<=Y[j]<v for x,y,u,v in d["blocked"])}
    src=next((i,j) for i,j in free if X[i]<=start[0]<X[i+1] and Y[j]<=start[1]<Y[j+1])
    def crossing(a,b):
        i,j=a;k,l=b
        fees=[]
        for wall in d["walls"]:
            x,y,u,v=wall["segment"]
            if (i!=k and x==u==X[max(i,k)] and min(y,v)<=Y[j]<max(y,v)) or (j!=l and y==v==Y[max(j,l)] and min(x,u)<=X[i]<max(x,u)):
                fees.append(wall["fee"])
        return None if None in fees else sum(fees)
    dist={src:0}
    if independent:
        # Independent label-correcting relaxation over all undirected cell sides.
        sides=[(a,b,crossing(a,b)) for a in free for b in [(a[0]+1,a[1]),(a[0],a[1]+1)] if b in free]
        for _ in range(len(free)):
            changed=False
            for a,b,fee in sides:
                if fee is None:continue
                for u,v in ((a,b),(b,a)):
                    if u in dist and (v not in dist or dist[u]+fee<dist[v]):
                        dist[v]=dist[u]+fee;changed=True
            if not changed:break
    else:
        heap=[(0,src)]
        while heap:
            cost,a=heappop(heap)
            if dist[a]!=cost:continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                b=(a[0]+dx,a[1]+dy)
                if b not in free:continue
                fee=crossing(a,b)
                if fee is not None and (b not in dist or cost+fee<dist[b]):
                    dist[b]=cost+fee;heappush(heap,(cost+fee,b))
    fees=Counter();unreachable=0
    for i,j in free:
        area=(X[i+1]-X[i])*(Y[j+1]-Y[j])
        if (i,j) in dist:fees[str(dist[i,j])]+=area
        else:unreachable+=area
    return {"area_by_fee":dict(fees),"unreachable":unreachable}
