from itertools import combinations
from basis import add


def options(q,t,bases,history,stations):
    ps=q['packets'];where={p['id']:i for i,p in enumerate(ps)};candidates=[]
    for c in q['contacts']:
        si=stations.index(c['station']);band,until=history[si]
        if not c['start']<=t<c['end'] or band is not None and band!=c['band'] and t<=until:continue
        symbols=[]
        for s in c['symbols']:
            i=where[s['packet']];p=ps[i]
            if len(bases[i])==p['dimension'] or not p['release']<=t<p['deadline']:continue
            if any(len(bases[where[k]])!=ps[where[k]]['dimension'] for k in p['requires']):continue
            if len(add(bases[i],s['vector']))>len(bases[i]):symbols.append((i,s['vector']))
        actions=[]
        for n in range(1,min(c['rate'],len(symbols))+1):
            for selected in combinations(symbols,n):
                updated=list(bases);valid=True
                for i,v in selected:
                    new=add(updated[i],v)
                    if len(new)==len(updated[i]):valid=False;break
                    updated[i]=new
                if valid:actions.append((selected,updated))
        if actions:candidates.append((c,si,actions))
    def visit(i,occupied,state,hist,rows):
        if i==len(candidates):
            h=tuple((b,u) if u>=t+1 else (None,-1) for b,u in hist)
            yield tuple(state),h,tuple(rows);return
        c,si,actions=candidates[i];res={('s',c['station']),('c',c['craft']),('g',c['group'])}
        yield from visit(i+1,occupied,state,hist,rows)
        if res&occupied:return
        for selected,_ in actions:
            state2=list(state)
            for j,v in selected:state2[j]=add(state2[j],v)
            h=list(hist);h[si]=(c['band'],t+q['switch_cooldown'])
            extra=[dict(tick=t,contact=c['id'],packet=ps[j]['id'],vector=v) for j,v in selected]
            yield from visit(i+1,occupied|res,state2,h,rows+extra)
    yield from visit(0,set(),list(bases),list(history),[])
