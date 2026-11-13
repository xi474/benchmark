from functools import lru_cache
from semantic import connectivity,replay

def choices(q,t,battery,modes,locks,restrict=False):
    assets=q['assets'];connected=connectivity(q,t);local=[]
    for i,a in enumerate(assets):
        used=min(a['solar'][t],a['demand'][t]);charge=min(a['battery_capacity']-battery[i],a['solar'][t]-used);residual=a['demand'][t]-used;rows=[]
        for u in (False,True):
            if u and not connected[a['id']] or locks[i]>0 and u!=modes[i]:continue
            lock=(a['min_up'] if u else a['min_down'])-1 if u!=modes[i] else max(0,locks[i]-1);started=u and not modes[i]
            for g in range(min(residual,q['grid_capacity'][t])+1 if u else 1):
                if restrict and u and not g:continue
                for d in range(min(residual-g,a['battery_discharge_limit'],battery[i]+charge)+1):
                    rows.append((u,g,d,battery[i]+charge-d,lock,(a['priority']*(used+g+d),used+g+d,-a['startup_cost']*started)))
        local.append(rows)
    def visit(i,grid,ports,bs,us,ls,policy,score):
        if i==len(assets):yield tuple(bs),tuple(us),tuple(ls),dict(policy),score;return
        for u,g,d,b,l,value in local[i]:
            if grid+g>q['grid_capacity'][t] or ports+u>q['grid_ports'][t]:continue
            policy[assets[i]['id']]=(u,g,d)
            yield from visit(i+1,grid+g,ports+u,bs+[b],us+[u],ls+[l],policy,tuple(a+b for a,b in zip(score,value)))
            del policy[assets[i]['id']]
    yield from visit(0,0,0,[],[],[],{},(0,0,0))

def solve(q,independent=False,restrict=False):
    if independent:
        from commitment_mip import solve as other
        return other(q)
    selected={}
    @lru_cache(None)
    def value(t,battery,modes,locks):
        if t==q['periods']:return (0,0,0)
        best=None;chosen=None
        for bs,us,ls,p,score in choices(q,t,battery,modes,locks,restrict):
            future=value(t+1,bs,us,ls)
            if future is None:continue
            result=tuple(a+b for a,b in zip(score,future))
            if best is None or result>best:best=result;chosen=(bs,us,ls,p)
        selected[t,battery,modes,locks]=chosen;return best
    battery=tuple(a['battery_initial'] for a in q['assets']);modes=tuple(False for a in q['assets']);locks=tuple(0 for a in q['assets']);policy=[]
    assert value(0,battery,modes,locks) is not None
    for t in range(q['periods']):battery,modes,locks,p=selected[t,battery,modes,locks];policy.append(p)
    return replay(q,policy)
