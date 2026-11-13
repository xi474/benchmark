from collections import defaultdict


def terms(q):
    blocks={b['id']:b for b in q['cfg']['blocks']};weights={(r['pred'],r['succ']):r['frequency'] for r in q['edge_frequency']};pairs=defaultdict(int)
    for pred,b in blocks.items():
        for succ in b['successors']:
            for phi in blocks[succ]['phis']:
                u,v=phi['inputs'][pred],phi['def']
                if u!=v:pairs[tuple(sorted((u,v)))]+=weights[pred,succ]
    return dict(pairs)


def copy_cost(q,locations):return sum(weight for (u,v),weight in terms(q).items() if locations[u]!=locations[v])


def solve(q,a):
    variables=list(q['spill_cost']);weights=q['spill_cost'];pins=q['config']['precolors'];regs=q['config']['registers'];adj={v:set() for v in variables};affinity=terms(q)
    for u,v in a['interference']:adj[u].add(v);adj[v].add(u)
    base_domains={v:[r for r in regs if r not in a['call_forbidden'].get(v,[])] for v in variables};placed=dict(pins);best=None;answer=None
    def search(pending,spilled):
        nonlocal best,answer
        lower=sum(w for (u,v),w in affinity.items() if u in placed and v in placed and (placed[u]!=placed[v] or placed[u] is None))
        domains={v:[r for r in base_domains[v] if all(placed.get(n)!=r for n in adj[v])] for v in pending}
        forced=spilled+sum(weights[v] for v in pending if not domains[v])
        if best is not None and (forced>best[0] or forced==best[0] and lower>=best[1]):return
        if not pending:best=(spilled,lower);answer=dict(placed);return
        v=min(pending,key=lambda k:(len(domains[k]),-len(adj[k]&pending),-weights[k]));following=pending-{v}
        def affinity_gain(r):return sum(w for (u,z),w in affinity.items() if (u==v and z in placed and placed[z]==r) or (z==v and u in placed and placed[u]==r))
        for r in sorted(domains[v],key=lambda r:-affinity_gain(r)):
            placed[v]=r;search(following,spilled)
        placed[v]=None;search(following,spilled+weights[v]);del placed[v]
    search(set(variables)-pins.keys(),0)
    assert answer is not None
    return {v:'reg:'+r if r is not None else 'spill:'+v for v,r in answer.items()}
