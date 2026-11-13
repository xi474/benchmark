"""Weighted transaction isolation on a derived multi-version dependency graph."""
from collections import defaultdict,deque


def derive(q,direct):
    txs=q["transactions"]
    edges=set()
    def add(a,b,kind):
        if a!=b:edges.add((a,b,kind))
    keys={key for t in txs for key in t["writes"]}
    writers={key:sorted((t for t in txs if key in t["writes"]),key=lambda t:t["commit"]) for key in keys}
    for chain in writers.values():
        for earlier,later in zip(chain,chain[1:]):add(earlier["id"],later["id"],"WW")
    for t in txs:
        for r in t["reads"]:
            if r["writer"] is not None:add(r["writer"],t["id"],"WR")
            candidates=(w for w in txs if r["key"] in w["writes"]) if direct else writers.get(r["key"],[])
            for w in candidates:
                if w["commit"]>=t["start"]:add(t["id"],w["id"],"RW")
        for scan in t["scans"]:
            for key in keys-set(q["initial"])-set(scan["seen"]):
                if not key.startswith(scan["prefix"]):continue
                first=min((w for w in txs if key in w["writes"]),key=lambda t:t["commit"]) if direct else writers[key][0]
                if first["commit"]>=t["start"]:add(t["id"],first["id"],"PHANTOM")
    return edges


def corridor(q,graph,cost,enumerate_sets=False,greedy=False):
    start,end=q["from"],q["to"]
    protected=set(q["protected"])|{start,end}
    neighbors=defaultdict(set)
    for u,v,kind in graph:
        if kind in q["kinds"]:neighbors[u].add(v)
    def one_path(removed):
        queue=deque([start]);parent={start:None}
        while queue:
            a=queue.popleft()
            if a==end:
                path=[]
                while a is not None:path.append(a);a=parent[a]
                return path[::-1]
            for b in sorted(neighbors[a]):
                if b not in parent and b not in removed:parent[b]=a;queue.append(b)
        return None
    if greedy:
        removed=set()
        while (path:=one_path(removed)) is not None:
            options=set(path)-protected
            if not options:return None
            removed.add(min(options,key=lambda v:(cost[v],v)))
        return {"impact":sum(cost[v] for v in removed),"required":sorted(removed)}
    if enumerate_sets:
        best=None;intersection=set();visited=set()
        def branch(rem,weight):
            nonlocal best,intersection
            if rem in visited or (best is not None and weight>best):return
            visited.add(rem)
            path=one_path(rem)
            if path is None:
                if best is None or weight<best:best=weight;intersection=set(rem)
                else:intersection.intersection_update(rem)
            else:
                for v in sorted(set(path)-protected,key=cost.get):
                    branch(rem|{v},weight+cost[v])
        branch(frozenset(),0)
        return None if best is None else {"impact":best,"required":sorted(intersection)}
    inf=1+sum(cost.values())
    def mincut(immune):
        graph=defaultdict(dict)
        def link(u,v,capacity):
            graph[u][v]=graph[u].get(v,0)+capacity;graph[v].setdefault(u,0)
        for k,val in cost.items():link((k,0),(k,1),inf if k in immune else val)
        for u,vs in neighbors.items():
            for v in vs:link((u,1),(v,0),inf)
        total=0;s=(start,1);sink=(end,0)
        while total<inf:
            prev={s:None};todo=deque([s])
            while todo and sink not in prev:
                u=todo.popleft()
                for v,c in graph[u].items():
                    if c and v not in prev:prev[v]=u;todo.append(v)
            if sink not in prev:break
            arcs=[];v=sink
            while v!=s:arcs.append((prev[v],v));v=prev[v]
            amount=min(graph[u][v] for u,v in arcs);total+=amount
            for u,v in arcs:graph[u][v]-=amount;graph[v][u]+=amount
        return total
    best=mincut(protected)
    if best>=inf:return None
    required=sorted(v for v in cost.keys()-protected if mincut(protected|{v})>best) if best else []
    return {"impact":best,"required":required}


def solve(d,independent=False,greedy=False):
    G=derive(d,independent);cost={t["id"]:t["impact"] for t in d["transactions"]}
    return {"containment":{q["id"]:corridor(q,G,cost,independent,greedy) for q in d["queries"]}}
