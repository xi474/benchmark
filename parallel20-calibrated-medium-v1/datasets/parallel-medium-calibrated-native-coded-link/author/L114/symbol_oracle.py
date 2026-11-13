"""Independent received-symbol-set DP; no canonical-basis or primary choices imports."""
from functools import lru_cache
from itertools import combinations,product
from semantic import replay


@lru_cache(None)
def dimension(mask,k):
    vectors=[v for v in range(1,1<<k) if mask>>v&1]
    orthogonal=sum(all((v&z).bit_count()%2==0 for v in vectors) for z in range(1<<k))
    return k-orthogonal.bit_length()+1


def solve(q):
    packets=q['packets'];ids={p['id']:i for i,p in enumerate(packets)};stations=sorted({c['station'] for c in q['contacts']});end=max(c['end'] for c in q['contacts'])
    start=(tuple(0 for p in packets),tuple((None,-1) for s in stations));layer={start:[]}
    for t in range(end):
        following={}
        for (masks,history),trace in layer.items():
            ranks=[dimension(m,p['dimension']) for m,p in zip(masks,packets)];contacts=[];selections=[]
            for c in q['contacts']:
                si=stations.index(c['station']);old,until=history[si]
                if not c['start']<=t<c['end'] or old is not None and old!=c['band'] and t<=until:continue
                offered=[]
                for s in c['symbols']:
                    i=ids[s['packet']];p=packets[i]
                    if ranks[i]==p['dimension'] or not p['release']<=t<p['deadline']:continue
                    if any(ranks[ids[j]]<packets[ids[j]]['dimension'] for j in p['requires']):continue
                    if masks[i]>>s['vector']&1:continue
                    offered.append((i,s['vector']))
                variants=[()]+[xs for n in range(1,min(c['rate'],len(offered))+1) for xs in combinations(offered,n)]
                if len(variants)>1:contacts.append(c);selections.append(variants)
            for batch in product(*selections):
                used=[i for i,x in enumerate(batch) if x];legal=True
                for f in ['station','craft','group']:
                    if len({contacts[i][f] for i in used})<len(used):legal=False;break
                if not legal:continue
                after=list(masks);hist=list(history);rows=[]
                for ci in used:
                    c=contacts[ci];hist[stations.index(c['station'])]=(c['band'],t+q['switch_cooldown'])
                    for pi,v in batch[ci]:after[pi]|=1<<v;rows.append(dict(tick=t,contact=c['id'],packet=packets[pi]['id'],vector=v))
                hist=tuple((b,u) if u>=t+1 else (None,-1) for b,u in hist);key=(tuple(after),hist)
                if key not in following:following[key]=trace+rows
        layer=following
    def objective(item):
        masks=item[0][0];ranks=[dimension(m,p['dimension']) for m,p in zip(masks,packets)]
        return (sum(p['priority'] for p,r in zip(packets,ranks) if r==p['dimension']),sum(r==p['dimension'] for p,r in zip(packets,ranks)),sum(ranks))
    return replay(q,max(layer.items(),key=objective)[1])
