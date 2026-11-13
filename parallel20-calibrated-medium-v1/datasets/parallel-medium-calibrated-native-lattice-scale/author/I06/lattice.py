"""Exact integer measurement extrema using interval propagation and branch-and-bound."""
from math import gcd


def ceil_div(a,b):
    return -((-a)//b)


def propagate(initial,rows):
    bounds=dict(initial)
    changed=True
    while changed:
        changed=False
        for row in rows:
            terms={k:a for k,a in row["coefficients"].items() if a}
            low=sum(a*(bounds[k][0] if a>0 else bounds[k][1]) for k,a in terms.items())
            high=sum(a*(bounds[k][1] if a>0 else bounds[k][0]) for k,a in terms.items())
            if low>row["max"] or high<row["min"]:return None
            if row["min"]==row["max"]:
                fixed=sum(a*bounds[k][0] for k,a in terms.items() if bounds[k][0]==bounds[k][1])
                divisor=gcd(*(abs(a) for k,a in terms.items() if bounds[k][0]!=bounds[k][1]))
                if divisor and (row["min"]-fixed)%divisor:return None
            for k,a in terms.items():
                lo,hi=bounds[k]
                own_min=a*(lo if a>0 else hi)
                own_max=a*(hi if a>0 else lo)
                minimum=row["min"]-(high-own_max)
                maximum=row["max"]-(low-own_min)
                left=ceil_div(minimum,a) if a>0 else ceil_div(maximum,a)
                right=maximum//a if a>0 else minimum//a
                revised=max(lo,left),min(hi,right)
                if revised[0]>revised[1]:return None
                if revised!=(lo,hi):bounds[k]=revised;changed=True
    return bounds


def minimum(initial,rows,objective):
    best=None
    def search(box):
        nonlocal best
        bounds=propagate(box,rows)
        if bounds is None:return
        lower=sum(a*(bounds[k][0] if a>=0 else bounds[k][1]) for k,a in objective.items())
        if best is not None and lower>=best:return
        free=[k for k,(lo,hi) in bounds.items() if lo!=hi]
        if not free:
            best=lower;return
        pivot=min(free,key=lambda k:(bounds[k][1]-bounds[k][0],-abs(objective.get(k,0))))
        lo,hi=bounds[pivot]
        values=range(lo,hi+1) if objective.get(pivot,0)>=0 else range(hi,lo-1,-1)
        for value in values:
            child=dict(bounds);child[pivot]=(value,value)
            search(child)
            if best==lower:return
    search(initial)
    return best


def solve(q):
    bounds={k:tuple(v) for k,v in q["bounds"].items()}
    setups={}
    for setup in q["setups"]:
        rows=q["measurements"]+setup["extra"]
        feasible=minimum(bounds,rows,{}) is not None
        ranges=None
        if feasible:
            ranges={}
            for gauge in q["gauges"]:
                coefficients=gauge["coefficients"]
                lo=minimum(bounds,rows,coefficients)
                hi=-minimum(bounds,rows,{k:-a for k,a in coefficients.items()})
                ranges[gauge["id"]]=[gauge["base"]+lo,gauge["base"]+hi]
        setups[setup["id"]]={"feasible":feasible,"ranges":ranges}
    return {"setups":setups}
