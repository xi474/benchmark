from collections import deque
from itertools import combinations


def analyze(q):
    blocks={b['id']:b for b in q['cfg']['blocks']};variables=set(q['cfg']['parameters'])
    for b in blocks.values():variables.update(p['def'] for p in b['phis']);variables.update(i['def'] for i in b['instructions'] if i['def'] is not None)
    names=sorted(variables);bit={v:1<<i for i,v in enumerate(names)};phi={};defined={};use={};pred={k:[] for k in blocks}
    for k,b in blocks.items():
        for s in b['successors']:pred[s].append(k)
        phi[k]=sum(bit[p['def']] for p in b['phis']);seen=phi[k];needed=0
        for i in b['instructions']:
            for v in i['uses']:needed |= bit[v]&~seen
            if i['def'] is not None:seen|=bit[i['def']]
        defined[k]=seen;use[k]=needed
    incoming={k:0 for k in blocks};outgoing={k:0 for k in blocks};todo=deque(blocks);queued=set(blocks)
    while todo:
        k=todo.popleft();queued.remove(k);after=0
        for s in blocks[k]['successors']:
            after |= incoming[s]&~phi[s]
            for p in blocks[s]['phis']:after|=bit[p['inputs'][k]]
        before=use[k]|(after&~defined[k]);outgoing[k]=after
        if before!=incoming[k]:
            incoming[k]=before
            for p in pred[k]:
                if p not in queued:todo.append(p);queued.add(p)
    edges=set();forbidden={}
    def members(mask):return [v for v in names if bit[v]&mask]
    def clique(mask):edges.update(combinations(members(mask),2))
    for k,b in blocks.items():
        live=outgoing[k];clique(live)
        for i in reversed(b['instructions']):
            definition=i['def'];d=bit[definition] if definition is not None else 0
            if i['call']:
                for v in members(live&~d):forbidden.setdefault(v,set()).update(q['config']['call_clobbered'])
            if definition is not None:
                edges.update(tuple(sorted((definition,v))) for v in members(live&~d));live&=~d
            for v in i['uses']:live|=bit[v]
            clique(live)
        clique(live);clique(incoming[k])
    return dict(live_in={k:members(v) for k,v in incoming.items()},live_out={k:members(v) for k,v in outgoing.items()},
        interference=[list(e) for e in sorted(edges)],call_forbidden={k:sorted(v) for k,v in forbidden.items() if v})
