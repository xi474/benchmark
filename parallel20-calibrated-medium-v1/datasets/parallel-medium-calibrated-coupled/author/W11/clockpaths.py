"""Timing extrema with shared clock segments and consistent operating conditions."""
from collections import defaultdict
from graphlib import TopologicalSorter


def solve(d, independent=False, separate_clock=False):
    incoming=defaultdict(list)
    for e in d["edges"]:incoming[e["to"]].append(e)
    order=list(TopologicalSorter({n:[e["from"] for e in incoming[n]] for n in d["nodes"]}).static_order())
    prohibited=[tuple(w) for w in d["forbidden"]]
    prefixes={()}|{word[:i] for word in prohibited for i in range(1,len(word))}
    def step(prefix,node):
        word=prefix+(node,)
        if any(word[-len(p):]==p for p in prohibited):return None
        return max((p for p in prefixes if not p or word[-len(p):]==p),key=len)
    answers={}
    for corner in d["corners"]:
        def clock_delta(source,terminal):
            left=d["launch_clock"][source];right=terminal["capture_clock"]
            shared=set(left)&set(right)
            if independent:
                coeff={e:int(e in left)-int(e in right) for e in set(left+right)}
                return tuple(sum((min if i==0 else max)(a*corner["clock"][e][0],a*corner["clock"][e][1]) for e,a in coeff.items()) for i in range(2))
            if not separate_clock:
                left=[e for e in left if e not in shared];right=[e for e in right if e not in shared]
            return (sum(corner["clock"][e][0] for e in left)-sum(corner["clock"][e][1] for e in right),
                    sum(corner["clock"][e][1] for e in left)-sum(corner["clock"][e][0] for e in right))
        def consider(endpoint,src,lo,hi):
            t=d["endpoints"][endpoint];a,b=clock_delta(src,t)
            values=[t["period"]-t["setup"]-hi-b,lo+a-t["hold"]]
            row=answers.setdefault(endpoint,dict(setup=None,hold=None))
            for key,v in zip(("setup","hold"),values):
                row[key]=v if row[key] is None else min(row[key],v)
        if independent:
            outgoing=defaultdict(list)
            for e in d["edges"]:outgoing[e["from"]].append(e)
            def visit(src,path,lo,hi):
                if any(path[-len(p):]==p for p in prohibited):return
                end=path[-1]
                if end in d["endpoints"]:consider(end,src,lo,hi)
                for edge in outgoing[end]:
                    a,b=corner["data"][edge["id"]];visit(src,path+(edge["to"],),lo+a,hi+b)
            for src in d["launch_clock"]:visit(src,(src,),0,0)
            continue
        extrema={}
        for n in order:
            states={}
            if n in d["launch_clock"]:
                prefix=step((),n)
                if prefix is not None:states[n,prefix]=0,0
            for e in incoming[n]:
                a,b=corner["data"][e["id"]]
                for (src,p),(lo,hi) in extrema[e["from"]].items():
                    q=step(p,n)
                    if q is None:continue
                    key=src,q;low,high=lo+a,hi+b
                    if key in states:low=min(low,states[key][0]);high=max(high,states[key][1])
                    states[key]=low,high
            extrema[n]=states
            if n in d["endpoints"]:
                for (src,_),(lo,hi) in states.items():consider(n,src,lo,hi)
    return {"slack":{k:answers.get(k) for k in d["endpoints"]}}
