"""Weighted scheduling on the product order of causality and review sessions."""
from collections import deque
from graphlib import TopologicalSorter


def structure(request):
    events={e["id"]:e for e in request["events"]}
    order=list(TopologicalSorter({k:e["parents"] for k,e in events.items()}).static_order())
    prior={}
    for k in order:
        parents=events[k]["parents"]
        prior[k]=set(parents).union(*(prior[p] for p in parents))
    return events,order,prior


def solve_registered(d, independent=False, myopic=False):
    events,order,prior=structure(d)
    def enumerate_sessions(valid,assigned):
        candidates=[k for k in order if valid[k]]
        upper=[0]*(len(candidates)+1)
        for j in reversed(range(len(candidates))):upper[j]=upper[j+1]+events[candidates[j]]["value"]
        best=-1;answer={}
        def visit(j,placed,worth):
            nonlocal best,answer
            if worth+upper[j]<=best:return
            if j==len(candidates):
                best=worth;answer=dict(placed);return
            n=candidates[j]
            for slot in valid[n]:
                if any((p in prior[n] and s>=slot) or (n in prior[p] and s<=slot) for p,s in placed.items()):
                    continue
                placed[n]=slot
                visit(j+1,placed,worth+events[n]["value"])
                del placed[n]
            visit(j+1,placed,worth)
        visit(0,dict(assigned),0)
        return answer
    if myopic:
        chosen={}
        for slot in range(1,d["sessions"]+1):
            valid={k:[slot] if k not in chosen and slot in e["slots"] else [] for k,e in events.items()}
            chosen=enumerate_sessions(valid,chosen)
    elif independent:
        chosen=enumerate_sessions({k:e["slots"] for k,e in events.items()},{})
    else:
        # A feasible schedule is an antichain of (event, session) copies.
        copies=[(k,j) for k in order for j in events[k]["slots"]]
        cap=sum(events[k]["value"] for k,_ in copies)+1
        net={}
        def edge(a,b,c):
            net.setdefault(a,{})[b]=c;net.setdefault(b,{}).setdefault(a,0)
        for i,(a,s) in enumerate(copies):
            edge("start",("L",i),events[a]["value"])
            edge(("R",i),"end",events[a]["value"])
            for j,(b,t) in enumerate(copies):
                if (a in prior[b] and s>=t) or (a==b and s>t):
                    edge(("L",i),("R",j),cap)
        while True:
            queue=deque(["start"]);seen={"start":None}
            while queue:
                a=queue.popleft()
                for b,v in net.get(a,{}).items():
                    if v and b not in seen:seen[b]=a;queue.append(b)
            if "end" not in seen:break
            path=[];v="end"
            while seen[v] is not None:path.append((seen[v],v));v=seen[v]
            amount=min(net[a][b] for a,b in path)
            for a,b in path:net[a][b]-=amount;net[b][a]+=amount
        chosen={a:s for i,(a,s) in enumerate(copies) if ("L",i) in seen and ("R",i) not in seen}
    return {"schedule":chosen}

from functools import lru_cache
def frontier_oracle(d):
    events={e["id"]:e for e in d["events"]}
    parents={k:e["parents"] for k,e in events.items()}
    order=list(TopologicalSorter(parents).static_order())
    index={k:i for i,k in enumerate(order)}
    last=dict(index)
    for k,ps in parents.items():
        for p in ps:last[p]=max(last[p],index[k])
    boundary=[tuple(k for k in order[:j] if last[k]>=j) for j in range(len(order)+1)]
    selected={}
    @lru_cache(None)
    def optimize(j,values):
        if j==len(order):return 0
        prev=dict(zip(boundary[j],values));k=order[j];e=events[k]
        earliest=max((prev[p] for p in e["parents"]),default=0)
        options=[(earliest,0,None)]+[(s,e["value"],s) for s in e["slots"] if s>earliest]
        best=-1
        for propagated,bonus,slot in options:
            prev[k]=propagated
            future=tuple(prev[n] for n in boundary[j+1]);worth=bonus+optimize(j+1,future)
            if worth>best:
                best=worth;selected[j,values]=slot,future
        return best
    optimize(0,());values=();answer={}
    for j,k in enumerate(order):
        s,values=selected[j,values]
        if s is not None:answer[k]=s
    return {"schedule":answer}


def solve(d,independent=False):
    return frontier_oracle(d) if independent else solve_registered(d)

def shortcut(d):
    # Give every session the best remaining same-session antichain; use the exact
    # polynomial solver for that one-session problem to keep the control fast.
    chosen={}
    events,order,prior=structure(d)
    for slot in range(1,d["sessions"]+1):
        restricted=[]
        for k,e in events.items():
            allowed=k not in chosen and slot in e["slots"] and all(k not in prior[p] for p in chosen)
            restricted.append({**e,"slots":[slot] if allowed else []})
        chosen.update(solve_registered({**d,"events":restricted})["schedule"])
    return {"schedule":chosen}
